import logging
from social_core.services.interfaces import SocialAPI

logger = logging.getLogger(__name__)


class InstagramAPI(SocialAPI):
    """Instagram向けスタブAPIクライアント"""

    def fetch_posts(self, account, since=None, until=None):
        logger.info("IG fetch_posts: %s", account)
        return []

    def publish_post(self, account, caption, media_url=None):
        logger.info("IG publish_post: %s %s", account, caption)
        return {"id": "dummy"}

    def send_dm(self, account, user, text):
        logger.info("IG send_dm: %s -> %s : %s", account, user, text)
        return True

    def get_insights(self, account, since, until):
        logger.info("IG get_insights: %s", account)
        return {}
