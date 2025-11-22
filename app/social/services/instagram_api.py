"""Instagram API クライアントのスタブ"""
from datetime import datetime
from typing import List, Dict


def fetch_posts(access_token: str, user_id: str, since: datetime | None = None) -> List[Dict]:
    dummy = {
        'id': 'ig1',
        'content': 'Instagramテスト投稿',
        'like_count': 2,
        'view_count': 5,
        'posted_at': datetime.now().isoformat(),
    }
    return [dummy]


def post_instagram(access_token: str, user_id: str, text: str) -> Dict:
    return {'id': 'posted', 'text': text}
