# src/api/slack_handler.py

from fastapi import APIRouter, Request, HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import os
from typing import Dict

from ..search.hybrid_searcher import HybridSearcher
from ..config import TOP_K

router = APIRouter()
searcher = HybridSearcher()

# initialize slack client
slack_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_token)

def verify_slack_request(request: Request) -> bool:
    """verify the request is coming from Slack"""
    # in production, implement Slack signature verification here
    return True

def format_search_results(results: list) -> str:
    """format search results for Slack message"""
    if not results:
        return "No results found."
    
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_results.append(
            f"*{i}.* Score: {result['score']:.2f}\n"
            f"```{result['text'][:300]}...```\n"
            f"Source: {result['metadata'].get('filename', 'Unknown')}\n"
        )
    
    return "\n".join(formatted_results)

@router.post("/slack/events")
async def handle_slack_events(request: Request):
    """handle Slack events API"""
    body = await request.body()
    event_data = json.loads(body)
    
    # handle url verification
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    if not verify_slack_request(request):
        raise HTTPException(status_code=401, detail="Invalid request")

    event = event_data.get("event", {})
    if event.get("type") == "app_mention":
        channel = event.get("channel")
        text = event.get("text")
        
        # remove the bot mention from the query
        query = text.split(">", 1)[1].strip() if ">" in text else text
        
        try:
            # perform search
            results = searcher.search(query, TOP_K)
            
            # format and send response
            response = format_search_results(results)
            client.chat_postMessage(
                channel=channel,
                text=f"Results for: *{query}*\n\n{response}"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=channel,
                text=f"sorry, I encountered an error: {str(e)}"
            )
    
    return {"ok": True}

@router.post("/slack/commands")
async def handle_slack_commands(request: Request):
    """handle Slack slash commands"""
    form_data = await request.form()
    command = form_data.get("command")
    text = form_data.get("text")
    
    if command == "/search":
        try:
            results = searcher.search(text, TOP_K)
            response = format_search_results(results)
            return {
                "response_type": "in_channel",
                "text": f"Results for: *{text}*\n\n{response}"
            }
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"sorry, I encountered an error: {str(e)}"
            }
    
    return {"text": "Unknown command"}
