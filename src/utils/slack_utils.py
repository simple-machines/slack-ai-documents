# src/utils/slack_utils.py

import hmac
import hashlib
import time
from typing import Dict, List, Optional
from fastapi import Request, HTTPException
import logging
from ..config import (
    SLACK_SIGNING_SECRET,
    SLACK_RESULT_CHUNK_SIZE,
    SLACK_MAX_RESULTS
)

logger = logging.getLogger(__name__)

async def verify_slack_request(request: Request) -> bool:
    """Verify request is coming from Slack using signing secret"""
    if not SLACK_SIGNING_SECRET:
        raise HTTPException(status_code=500, detail="Slack signing secret not configured")
        
    slack_signature = request.headers.get("X-Slack-Signature", "")
    slack_timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    
    if abs(time.time() - float(slack_timestamp)) > 60 * 5:
        raise HTTPException(status_code=403, detail="Request too old")
        
    body = await request.body()
    sig_basestring = f"v0:{slack_timestamp}:{body.decode()}"
    my_signature = f"v0={hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()}"
    
    if not hmac.compare_digest(my_signature, slack_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
        
    return True

def format_search_results(results: List[Dict], query: str, thread_ts: Optional[str] = None) -> Dict:
    """Format find results as Slack blocks"""
    if not results:
        return {
            "response_type": "in_channel",
            "thread_ts": thread_ts,
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No results found for your query."
                }
            }]
        }
    
    blocks = [{
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"🔍 Results for: {query}"
        }
    }]
    
    # Limit results
    results = results[:SLACK_MAX_RESULTS]
    
    for i, result in enumerate(results, 1):
        # Add divider between results
        if i > 1:
            blocks.append({"type": "divider"})
            
        # Add result block with truncated text
        text = result['text']
        if len(text) > SLACK_RESULT_CHUNK_SIZE:
            text = text[:SLACK_RESULT_CHUNK_SIZE] + "..."
            
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Result {i}* (Score: {result['score']:.2f})\n```{text}```"
            }
        })
        
        # Add context with metadata
        context_elements = []
        if result['metadata'].get('filename'):
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Source:* {result['metadata']['filename']}"
            })
        if result.get('found_by'):
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Found by:* {', '.join(result['found_by'])}"
            })
            
        if context_elements:
            blocks.append({
                "type": "context",
                "elements": context_elements
            })
    
    return {
        "response_type": "in_channel",
        "thread_ts": thread_ts,
        "blocks": blocks
    }

def extract_query(text: str, bot_user_id: str = None) -> str:
    """Extract query from message text, removing bot mention if present"""
    if bot_user_id and f"<@{bot_user_id}>" in text:
        return text.split(f"<@{bot_user_id}>")[1].strip()
    return text.strip()