from abc import ABC, abstractmethod


class SocialAPI(ABC):
    """各SNS APIクライアント共通インターフェース"""

    @abstractmethod
    def fetch_posts(self, account, since=None, until=None):
        raise NotImplementedError

    @abstractmethod
    def publish_post(self, account, caption, media_url=None):
        raise NotImplementedError

    @abstractmethod
    def send_dm(self, account, user, text):
        raise NotImplementedError

    @abstractmethod
    def get_insights(self, account, since, until):
        raise NotImplementedError
