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

def group_results_by_source(results: List[Dict]) -> List[Dict]:
    """Group search results by their source document"""
    grouped = {}
    
    for result in results:
        source = result['metadata'].get('filename', 'Unknown')
        if source not in grouped:
            grouped[source] = {
                'source': source,
                'passages': [],
                'scores': [],
                'explanations': [],
                'metadata': result['metadata']
            }
        
        grouped[source]['passages'].append(result['text'])
        grouped[source]['scores'].append(result['score'])
        grouped[source]['explanations'].append(
            result['metadata'].get('relevance_explanation', '')
        )
    
    # Convert to list and format each group
    formatted_results = []
    for source_data in grouped.values():
        # Combine explanations
        combined_explanation = "Based on these passages: " + \
                             " Additionally, ".join(source_data['explanations'])
        
        # Get highest score
        max_score = max(source_data['scores'])
        
        formatted_results.append({
            'source': source_data['source'],
            'passages': source_data['passages'],
            'score': max_score,
            'explanation': combined_explanation,
            'metadata': source_data['metadata']
        })
    
    return formatted_results

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

    # Group results by source
    grouped_results = group_results_by_source(results)

    # Create the text version for notifications/screen readers
    text_content = f"Search Results for: {query}\n"
    for result in grouped_results:
        text_content += f"\nsource: {result['source']}\n"
        for i, passage in enumerate(result['passages'], 1):
            text_content += f"passage {i}: {passage}\n"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🖨️ *results for:* _{query}_"
            }
        }
    ]

    for result in grouped_results:
        # Format passages
        passages_text = ""
        for i, passage in enumerate(result['passages'], 1):
            passages_text += f"*passage {i}:* {passage}\n\n"

        main_text = f"*source:* {result['source']}\n\n"
        main_text += passages_text
        main_text += f"*explanation:* _{result['explanation']}_\n"

        result_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": main_text
                }
            }
        ]

        # Add download button if link is available
        download_link = result['metadata'].get('download_link', '')
        if download_link:
            result_block.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📥 Download Document",
                            "emoji": True
                        },
                        "url": download_link,
                        "action_id": f"download_doc_{result['source']}"
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
        "text": text_content,
        "blocks": blocks
    }

def extract_query(text: str, bot_user_id: str = None) -> str:
    """Extract query from message text, removing bot mention if present"""
    if bot_user_id and f"<@{bot_user_id}>" in text:
        return text.split(f"<@{bot_user_id}>")[1].strip()
    return text.strip()
