# src/api/slack_handler.py

from fastapi import APIRouter, Request, HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import logging
from typing import Dict, Optional
import asyncio

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
        searcher = get_searcher()
        results = await searcher.search(text)
        response = await format_search_results(results, text, "", thread_ts)
        client = get_slack_client()
        # await client.chat_postMessage(channel=channel_id, **response)
        client.chat_postMessage(channel=channel_id, **response)

    async def handle_mention(self, event: Dict):
        """handle app mention events"""
        try:
            channel = event.get("channel")
            text = event.get("text", "")
            user = event.get("user")
            thread_ts = event.get("thread_ts", event.get("ts"))

            logger.info("processing app mention", extra={
                "channel": channel,
                "user": user,
                "text_length": len(text)
            })

            client = get_slack_client()

            # extract query from mention
            query = extract_query(text)
            if not query:
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="please provide a search query! 🔍"
                )
                return {"ok": True}

            # perform search
            searcher = get_searcher()
            results = await searcher.search(query)

            # format and send response
            response = await format_search_results(results, query, "", thread_ts)
            await client.chat_postMessage(
                channel=channel,
                **response
            )

            logger.info("search results sent", extra={
                "channel": channel,
                "num_results": len(results)
            })

            return {"ok": True}

        except SlackApiError as e:
            logger.error("Slack API error", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error("error handling mention", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_slack_commands(self, request: Request):
        """handle Slack slash commands"""
        try:
            await verify_slack_request(request)

            form_data = await request.form()
            command = form_data.get("command")
            text = form_data.get("text", "").strip()
            channel_id = form_data.get("channel_id")
            user_id = form_data.get("user_id")
            thread_ts = form_data.get("thread_ts")

            logger.info("received slash command", extra={
                "command": command,
                "channel": channel_id,
                "user": user_id
            })

            if command == "/find":
                if not text:
                    response = {
                        "response_type": "ephemeral",
                        "text": "please provide a search query! Usage: `/find your query here`"
                    }
                    return response

                # respond immediately to slack
                response = {
                    "response_type": "ephemeral",
                    "text": "searching for results... please wait 🧑‍💻 it will take a little while but not long"
                }

                # process search asynchronously
                asyncio.create_task(self._async_search_and_respond(text, thread_ts, channel_id, user_id))

                return response

            return {
                "response_type": "ephemeral",
                "text": "Unknown command"
            }

        except Exception as e:
            logger.error("error handling slash command", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"sorry, I encountered an error: {str(e)}"
            }

# instantiate the SlackHandler
slack_handler = SlackHandler()

@router.post("/slack/events")
async def handle_slack_events(request: Request):
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
    return await slack_handler.handle_slack_commands(request)
