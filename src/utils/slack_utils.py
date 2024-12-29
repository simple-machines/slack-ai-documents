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

async def format_search_results(results: List[Dict], query: str, summary: str, thread_ts: Optional[str] = None) -> Dict:
    """Format search results for Slack message"""
    if not results:
        return {
            "response_type": "in_channel",
            "thread_ts": thread_ts,
            "text": "No results found for your query.",
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No results found for your query."
                }
            }]
        }

    # create the text version for notifications/screen readers
    text_content = f"Search Results for: {query}\n"
    for i, result in enumerate(results[:SLACK_MAX_RESULTS], 1):
        # text_content += f"\nresult {i} (score: {result['score']:.2f})\n"
        text_content += f"\nresult {i}\n"
        text_content += f"source: {result['metadata'].get('filename', 'Unknown')}\n"
        text_content += f"{result['text']}\n"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🧠 results for: {query}"
            }
        }
    ]

    for i, result in enumerate(results[:SLACK_MAX_RESULTS], 1):
        explanation = result['metadata'].get('relevance_explanation', 'No explanation provided')
        text = result['text']
        score = result['score']
        metadata = result['metadata']
        download_link = metadata.get('download_link', '')

        # create the main text block
        main_text = f"*RESULT {i} (score: {score:.2f})*\n"
        # main_text = f"*result {i}*\n"
        main_text += f"*source:* {metadata.get('filename', 'Unknown')}\n"
        main_text += f"*passage:* {text}\n"
        main_text += f"*explanation:* {explanation}\n"

        result_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": main_text
                }
            }
        ]

        # add download button if link is available
        if download_link:
            result_block.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*document link:* " + download_link
                }
            })
            result_block.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📥 download document",
                            "emoji": True
                        },
                        "url": download_link,
                        "action_id": f"download_doc_{i}"
                    }
                ]
            })

        result_block.append({
            "type": "divider"
        })
        
        blocks.extend(result_block)

    return {
        "response_type": "in_channel",
        "thread_ts": thread_ts,
        "text": text_content,  # add plain text version for notifications
        "blocks": blocks
    }

def extract_query(text: str, bot_user_id: str = None) -> str:
    """extract query from message text, removing bot mention if present"""
    if bot_user_id and f"<@{bot_user_id}>" in text:
        return text.split(f"<@{bot_user_id}>")[1].strip()
    return text.strip()
