import logging

logger = logging.getLogger(__name__)


def handle_incoming_dm(account, text):
    """受信DMに対する自動返信スタブ"""
    logger.info("auto reply for %s: %s", account, text)
    return None
