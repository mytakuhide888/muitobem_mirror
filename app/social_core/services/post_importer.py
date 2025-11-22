import logging

logger = logging.getLogger(__name__)


def import_all(account):
    """指定アカウントの全投稿を取り込むスタブ"""
    logger.info("import_all called for %s", account)
    return []


def sync_latest(account):
    """最新投稿のみ同期するスタブ"""
    logger.info("sync_latest called for %s", account)
    return []
