# src/api/slack_handler.py

from fastapi import APIRouter, Request, HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import logging
from typing import Dict, Optional
import asyncio
import random

from ..search.gemini_searcher import GeminiSearcher
from ..config import SLACK_BOT_TOKEN, TOP_P_THRESHOLD
from ..utils.slack_utils import verify_slack_request, format_search_results, extract_query

router = APIRouter()
logger = logging.getLogger(__name__)

# lazy initialization
_searcher = None
_client = None

def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = GeminiSearcher()
    return _searcher

def get_slack_client():
    global _client
    if _client is None:
        if not SLACK_BOT_TOKEN:
            raise ValueError("SLACK_BOT_TOKEN must be set")
        _client = WebClient(token=SLACK_BOT_TOKEN)
    return _client

class SlackHandler:
    def __init__(self):
        pass

    async def _async_search_and_respond(self, text: str, thread_ts: Optional[str], channel_id: str, user_id: str):
        """Execute search and send response with enhanced error handling and retries"""
        try:
            searcher = get_searcher()
            max_retries = 3
            retry_count = 0
            backoff_factor = 1.5
            
            while retry_count < max_retries:
                try:
                    # Send initial "processing" message
                    client = get_slack_client()
                    processing_msg = {
                        "channel": channel_id,
                        "thread_ts": thread_ts,
                        "text": "📡 processing your request..."
                    }
                    # Remove await - WebClient is not async
                    client.chat_postMessage(**processing_msg)
                    
                    # Perform search - this is async
                    results = await searcher.search(text)
                    response = await format_search_results(results, text, "", thread_ts)
                    # Remove await - WebClient is not async
                    client.chat_postMessage(channel=channel_id, **response)
                    break
                    
                except (BrokenPipeError, ConnectionError, SlackApiError) as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        # Send error message to user
                        error_msg = {
                            "channel": channel_id,
                            "thread_ts": thread_ts,
                            "text": "Sorry, I encountered a temporary connection issue. Please try again in a few moments. 🔄"
                        }
                        client = get_slack_client()
                        # Remove await - WebClient is not async
                        client.chat_postMessage(**error_msg)
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        return
                    
                    wait_time = (backoff_factor ** retry_count) + random.uniform(0, 1)
                    logger.warning(f"Search attempt {retry_count} failed. Retrying in {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                    
        except Exception as e:
            logger.error(f"Error in async search and respond: {str(e)}", exc_info=True)
            error_msg = {
                "channel": channel_id,
                "thread_ts": thread_ts,
                "text": "Sorry, I encountered an unexpected error. Please try again later. 🚫"
            }
            client = get_slack_client()
            # Remove await - WebClient is not async
            client.chat_postMessage(**error_msg)

    async def handle_mention(self, event: Dict):
        """Handle app mention events with enhanced error handling"""
        try:
            channel = event.get("channel")
            text = event.get("text", "")
            user = event.get("user")
            thread_ts = event.get("thread_ts", event.get("ts"))

            logger.info("Processing app mention", extra={
                "channel": channel,
                "user": user,
                "text_length": len(text)
            })

            client = get_slack_client()

            # Extract query from mention
            query = extract_query(text)
            if not query:
                # Remove await - WebClient is not async
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="Please provide a search query! 🔍"
                )
                return {"ok": True}

            # Process search asynchronously
            asyncio.create_task(
                self._async_search_and_respond(query, thread_ts, channel, user)
            )

            return {"ok": True}

        except SlackApiError as e:
            logger.error("Slack API error", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error("Error handling mention", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_slack_commands(self, request: Request):
        """Handle Slack slash commands with enhanced error handling"""
        try:
            await verify_slack_request(request)

            form_data = await request.form()
            command = form_data.get("command")
            text = form_data.get("text", "").strip()
            channel_id = form_data.get("channel_id")
            user_id = form_data.get("user_id")
            thread_ts = form_data.get("thread_ts")

            logger.info("Received slash command", extra={
                "command": command,
                "channel": channel_id,
                "user": user_id
            })

            if command == "/find":
                # Check if text is empty
                if not text:
                    return {
                        "response_type": "ephemeral",
                        "text": "Please provide a search query! Usage: `/find [how to apply for leave]` 🔍"
                    }
                
                # Check text length and word count
                word_count = len(text.split())
                if len(text) < 10 or word_count < 2:
                    return {
                        "response_type": "ephemeral",
                        "text": "your query is too short, please provide at least 3 words, for example: `/find [how to apply for leave]` 📝"
                    }

                # Respond immediately to slack
                response = {
                    "response_type": "ephemeral",
                    "text": "searching for results... please wait a minute 🧑‍💻"
                }

                # Process search asynchronously
                asyncio.create_task(
                    self._async_search_and_respond(text, thread_ts, channel_id, user_id)
                )

                return response

            return {
                "response_type": "ephemeral",
                "text": "Unknown command ❌"
            }

        except Exception as e:
            logger.error("Error handling slash command", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"Sorry, I encountered an error: {str(e)} 🚫"
            }

# Instantiate the SlackHandler
slack_handler = SlackHandler()

@router.post("/slack/events")
async def handle_slack_events(request: Request):
    """Handle Slack events with enhanced error handling"""
    try:
        # Get the raw request body as bytes first
        body_bytes = await request.body()
        # Parse it to json
        body = json.loads(body_bytes)
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # Verify request (only after challenge verification)
        await verify_slack_request(request)
        
        # Handle app mention events
        if body.get("event", {}).get("type") == "app_mention":
            return await slack_handler.handle_mention(body["event"])
        
        # Return ok for other events
        return {"ok": True}

    except Exception as e:
        logger.error("Error handling slack event", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack/commands")
async def handle_commands(request: Request):
    """Route for handling Slack slash commands"""
    return await slack_handler.handle_slack_commands(request)