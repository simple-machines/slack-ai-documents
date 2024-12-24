# src/api/slack_handler.py

from fastapi import APIRouter, Request, HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import logging
from typing import Dict

from ..search.hybrid_searcher import HybridSearcher
from ..config import SLACK_BOT_TOKEN, TOP_K
from ..utils.slack_utils import verify_slack_request, format_search_results, extract_query

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize searcher and Slack client
searcher = HybridSearcher()
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN must be set")
client = WebClient(token=SLACK_BOT_TOKEN)

@router.post("/slack/events")
async def handle_slack_events(request: Request):
    """Handle Slack events API"""
    try:
        body = await request.body()
        event_data = json.loads(body)
        
        # Log incoming event
        logger.info("Received Slack event", extra={
            "event_type": event_data.get("type"),
            "team_id": event_data.get("team_id"),
            "api_app_id": event_data.get("api_app_id")
        })
        
        # Handle URL verification
        if event_data.get("type") == "url_verification":
            return {"challenge": event_data.get("challenge")}

        # Verify request
        await verify_slack_request(request)

        event = event_data.get("event", {})
        if event.get("type") == "app_mention":
            return await handle_mention(event)
        
        return {"ok": True}
    
    except Exception as e:
        logger.error("Error handling Slack event", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def handle_mention(event: Dict):
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
        
        # Extract query from mention
        query = extract_query(text)
        if not query:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="Please provide a search query! 🔍"
            )
            return {"ok": True}
        
        # Perform search
        results = searcher.search(query, TOP_K)
        
        # Format and send response
        response = format_search_results(results, query, thread_ts)
        client.chat_postMessage(
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

@router.post("/slack/commands")
async def handle_slack_commands(request: Request):
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
        
        if command == "/find":  # Changed from /search to /find
            if not text:
                return {
                    "response_type": "ephemeral",
                    "text": "Please provide a search query! Usage: `/find your query here`"
                }
            
            results = searcher.search(text, TOP_K)
            return format_search_results(results, text, thread_ts)
            
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
