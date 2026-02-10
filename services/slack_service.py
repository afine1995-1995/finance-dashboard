import logging

from slack_sdk import WebClient

from config import Config

logger = logging.getLogger(__name__)

_client = None


def get_client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient(token=Config.SLACK_BOT_TOKEN)
    return _client


def post_message(blocks: list, text: str = "", channel: str = None, thread_ts: str = None):
    """Post a message to Slack with Block Kit blocks."""
    client = get_client()
    channel = channel or Config.SLACK_CHANNEL_ID
    kwargs = {
        "channel": channel,
        "blocks": blocks,
        "text": text or "Finance Dashboard notification",
    }
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    resp = client.chat_postMessage(**kwargs)
    return resp
