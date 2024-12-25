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
    """verify request is coming from Slack using signing secret"""
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

async def format_search_results(results: List[Dict], query: str, summary: str, thread_ts: Optional[str] = None) -> Dict:
    """format search results using multiple Slack blocks for each result"""
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

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 Results for: {query}"
            }
        }
    ]

    # add each result as a separate section block
    for i, result in enumerate(results[:SLACK_MAX_RESULTS], 1):
        explanation = result['metadata'].get('relevance_explanation', 'No explanation provided.')
        text = result['text']
        score = result['score']
        metadata = result['metadata']

        result_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Result {i} (Score: {score:.2f})*\n*Explanation:* {explanation}\n*Passage:* {text[:SLACK_RESULT_CHUNK_SIZE]}..."
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Source:* {metadata.get('filename', 'Unknown')}"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        blocks.extend(result_block)

    return {
        "response_type": "in_channel",
        "thread_ts": thread_ts,
        "blocks": blocks
    }

def extract_query(text: str, bot_user_id: str = None) -> str:
    """extract query from message text, removing bot mention if present"""
    if bot_user_id and f"<@{bot_user_id}>" in text:
        return text.split(f"<@{bot_user_id}>")[1].strip()
    return text.strip()
