# src/api/slack_handler.py

from fastapi import APIRouter, Request, HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import logging
from typing import Dict, Optional
import asyncio

from ..search.gemini_searcher import GeminiSearcher
from ..config import SLACK_BOT_TOKEN, TOP_K
from ..utils.slack_utils import verify_slack_request, format_search_results, extract_query

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization
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
        searcher = get_searcher()
        results = await searcher.search(text, TOP_K)
        response = await format_search_results(results, text, "", thread_ts) # Added missing summary argument
        client = get_slack_client()
        await client.chat_postMessage(channel=channel_id, **response)

    async def handle_mention(self, event: Dict):
        """Handle app mention events"""
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
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="Please provide a search query! 🔍"
                )
                return {"ok": True}

            # Perform search
            searcher = get_searcher()
            results = await searcher.search(query, TOP_K)

            # Format and send response
            response = await format_search_results(results, query, "", thread_ts) # Added missing summary argument
            await client.chat_postMessage(
                channel=channel,
                **response
            )

            logger.info("Search results sent", extra={
                "channel": channel,
                "num_results": len(results)
            })

            return {"ok": True}

        except SlackApiError as e:
            logger.error("Slack API error", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error("Error handling mention", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_slack_commands(self, request: Request):
        """Handle Slack slash commands"""
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
                if not text:
                    response = {
                        "response_type": "ephemeral",
                        "text": "Please provide a search query! Usage: `/find your query here`"
                    }
                    return response

                # Respond immediately to Slack
                response = {
                    "response_type": "ephemeral",
                    "text": "Searching for results... please wait 🧑‍💻"
                }

                # Process search asynchronously
                asyncio.create_task(self._async_search_and_respond(text, thread_ts, channel_id, user_id))

                return response

            return {
                "response_type": "ephemeral",
                "text": "Unknown command"
            }

        except Exception as e:
            logger.error("Error handling slash command", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"Sorry, I encountered an error: {str(e)}"
            }

# Instantiate the SlackHandler
slack_handler = SlackHandler()

@router.post("/slack/events")
async def handle_slack_events(request: Request):
    return await slack_handler.handle_slack_events(request)

@router.post("/slack/commands")
async def handle_commands(request: Request):
    return await slack_handler.handle_slack_commands(request)