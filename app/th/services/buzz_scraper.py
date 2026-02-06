# -*- coding: utf-8 -*-
"""
Threads バズ投稿スクレイパー
Playwright (stealth) を使用して Threads 検索結果をスクレイピングする。
Docker 環境では既にインストール済みの Chromium を使用する。
"""
import json
import logging
import os
import random
import re
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── 設定 ───

class ScraperConfig:
    """スクレイピング設定"""
    MIN_DELAY = 3          # 最小待機秒数
    MAX_DELAY = 8          # 最大待機秒数
    REQUESTS_PER_HOUR = 60 # 1時間あたりの最大リクエスト数
    MAX_SCROLL_COUNT = 5   # 検索結果ページのスクロール回数
    HEADLESS = True        # ヘッドレスモード（Docker環境用）

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]


# ─── レート制限 ───

class RateLimiter:
    """レート制限管理"""

    def __init__(self, requests_per_hour: int = ScraperConfig.REQUESTS_PER_HOUR):
        self.requests_per_hour = requests_per_hour
        self.request_times: List[float] = []

    def wait_if_needed(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 3600]

        if len(self.request_times) >= self.requests_per_hour:
            oldest = self.request_times[0]
            wait_time = 3600 - (now - oldest) + random.uniform(5, 15)
            logger.info("レート制限: %.0f秒待機", wait_time)
            time.sleep(wait_time)

        delay = random.uniform(ScraperConfig.MIN_DELAY, ScraperConfig.MAX_DELAY)
        time.sleep(delay)
        self.request_times.append(time.time())


# ─── バズ判定 ───

class ViralityDetector:
    """バズ判定ロジック"""

    # エンゲージメント重み付け
    WEIGHTS = {
        'replies': 3.0,
        'reposts': 2.5,
        'likes': 1.0,
    }

    # フォロワー数による閾値
    TIERS = {
        'micro': {    # 〜1万
            'min_likes': 500,
            'min_replies': 50,
            'engagement_rate': 5.0,
        },
        'mid': {      # 〜10万
            'min_likes': 5000,
            'min_replies': 200,
            'engagement_rate': 3.0,
        },
        'macro': {    # 10万+
            'min_likes': 50000,
            'min_replies': 1000,
            'engagement_rate': 2.0,
        },
    }

    @classmethod
    def calc_engagement_score(cls, post_data: Dict) -> float:
        return (
            post_data.get('like_count', 0) * cls.WEIGHTS['likes']
            + post_data.get('reply_count', 0) * cls.WEIGHTS['replies']
            + post_data.get('repost_count', 0) * cls.WEIGHTS['reposts']
        )

    @classmethod
    def calc_engagement_rate(cls, post_data: Dict, followers: int) -> float:
        if not followers or followers <= 0:
            return 0.0
        total = (
            post_data.get('like_count', 0)
            + post_data.get('reply_count', 0)
            + post_data.get('repost_count', 0)
        )
        return (total / followers) * 100

    @classmethod
    def is_viral(cls, post_data: Dict, followers: int) -> Dict:
        if followers is None or followers <= 0:
            tier = 'micro'
        elif followers < 10000:
            tier = 'micro'
        elif followers < 100000:
            tier = 'mid'
        else:
            tier = 'macro'

        threshold = cls.TIERS[tier]
        engagement_rate = cls.calc_engagement_rate(post_data, followers)
        engagement_score = cls.calc_engagement_score(post_data)

        meets_likes = post_data.get('like_count', 0) >= threshold['min_likes']
        meets_replies = post_data.get('reply_count', 0) >= threshold['min_replies']
        meets_rate = engagement_rate >= threshold['engagement_rate']

        viral = (meets_likes or meets_replies) and meets_rate

        return {
            'is_viral': viral,
            'engagement_rate': round(engagement_rate, 2),
            'engagement_score': round(engagement_score, 2),
            'tier': tier,
        }


# ─── ブラウザ管理 ───

def _find_chromium() -> str:
    """システムにインストール済みの Chromium パスを検索"""
    for candidate in ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']:
        path = shutil.which(candidate)
        if path:
            return path
    return '/usr/bin/chromium'


def _create_playwright_browser(headless: bool = True):
    """Playwright ブラウザインスタンスを生成"""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=headless,
        executable_path=_find_chromium(),
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ],
    )
    context = browser.new_context(
        viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
        user_agent=random.choice(ScraperConfig.USER_AGENTS),
        locale='ja-JP',
        timezone_id='Asia/Tokyo',
    )
    page = context.new_page()

    # webdriver プロパティを隠蔽
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    return pw, browser, context, page


# ─── メインスクレイパー ───

class ThreadsBuzzScraper:
    """Threads バズ投稿スクレイパー"""

    def __init__(self, headless: bool = ScraperConfig.HEADLESS):
        self.headless = headless
        self.rate_limiter = RateLimiter()
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_browser(self):
        if self._page is None:
            self._pw, self._browser, self._context, self._page = (
                _create_playwright_browser(self.headless)
            )

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._pw = self._browser = self._context = self._page = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ─── 検索 ───

    def search_keyword(self, keyword: str) -> List[Dict]:
        """キーワードで Threads を検索し、投稿を取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        search_url = f"https://www.threads.net/search?q={keyword}&serp_type=default"
        logger.info("検索開始: %s → %s", keyword, search_url)

        try:
            self._page.goto(search_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("ページ読み込みタイムアウト: %s (続行)", e)

        # スクロールして結果を追加読み込み
        posts = []
        for i in range(ScraperConfig.MAX_SCROLL_COUNT):
            new_posts = self._extract_posts_from_page(keyword)
            for p in new_posts:
                if p not in posts:
                    posts.append(p)

            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(random.uniform(1.5, 3.5))
            new_height = self._page.evaluate('document.body.scrollHeight')
            if new_height == prev_height:
                break

        logger.info("検索完了: %s → %d件取得", keyword, len(posts))
        return posts

    def _extract_posts_from_page(self, keyword: str) -> List[Dict]:
        """ページ上の投稿要素からデータを抽出"""
        posts = []
        try:
            # Threads の投稿コンテナを取得
            # セレクタは Threads の DOM 構造に依存するため、変更される可能性あり
            post_elements = self._page.query_selector_all('[data-pressable-container="true"]')
            if not post_elements:
                # フォールバック: article タグ
                post_elements = self._page.query_selector_all('article')
            if not post_elements:
                # フォールバック: div[role="article"]
                post_elements = self._page.query_selector_all('div[role="article"]')

            for el in post_elements:
                try:
                    post = self._parse_post_element(el, keyword)
                    if post and post.get('text_content'):
                        posts.append(post)
                except Exception as e:
                    logger.debug("投稿解析スキップ: %s", e)

        except Exception as e:
            logger.warning("投稿抽出エラー: %s", e)

        return posts

    def _parse_post_element(self, el, keyword: str) -> Optional[Dict]:
        """個別の投稿要素を解析"""
        text = ''
        username = ''
        display_name = ''
        like_count = 0
        reply_count = 0
        repost_count = 0
        post_url = ''

        # テキスト抽出
        text_el = el.query_selector('[dir="auto"]')
        if text_el:
            text = text_el.inner_text().strip()

        if not text:
            return None

        # ユーザー名抽出（@付きリンク）
        link_els = el.query_selector_all('a[href*="/@"]')
        for link in link_els:
            href = link.get_attribute('href') or ''
            match = re.search(r'/@([^/?]+)', href)
            if match:
                username = match.group(1)
                display_name = link.inner_text().strip()
                break

        # 投稿URLの抽出
        time_link = el.query_selector('a[href*="/post/"]')
        if time_link:
            href = time_link.get_attribute('href') or ''
            if href.startswith('/'):
                post_url = f"https://www.threads.net{href}"
            elif href.startswith('http'):
                post_url = href

        # エンゲージメント数の抽出
        like_count = self._extract_count(el, 'like')
        reply_count = self._extract_count(el, 'reply')
        repost_count = self._extract_count(el, 'repost')

        return {
            'text_content': text,
            'username': username,
            'display_name': display_name,
            'like_count': like_count,
            'reply_count': reply_count,
            'repost_count': repost_count,
            'post_url': post_url,
            'search_keyword': keyword,
        }

    def _extract_count(self, el, action_type: str) -> int:
        """いいね/リプライ/リポスト数を抽出"""
        try:
            # aria-label からの取得を試みる
            buttons = el.query_selector_all('div[role="button"]')
            for btn in buttons:
                label = btn.get_attribute('aria-label') or ''
                label_lower = label.lower()
                if action_type == 'like' and ('like' in label_lower or 'いいね' in label_lower):
                    return self._parse_count_text(label)
                elif action_type == 'reply' and ('reply' in label_lower or 'repl' in label_lower or '返信' in label_lower):
                    return self._parse_count_text(label)
                elif action_type == 'repost' and ('repost' in label_lower or 'リポスト' in label_lower):
                    return self._parse_count_text(label)
        except Exception:
            pass
        return 0

    @staticmethod
    def _parse_count_text(text: str) -> int:
        """テキストから数値を抽出 (例: '1.2K', '500', '1万')"""
        numbers = re.findall(r'[\d,.]+[KkMm万]?', text)
        for n in numbers:
            n = n.replace(',', '')
            if n.endswith(('K', 'k')):
                return int(float(n[:-1]) * 1000)
            elif n.endswith(('M', 'm')):
                return int(float(n[:-1]) * 1000000)
            elif n.endswith('万'):
                return int(float(n[:-1]) * 10000)
            else:
                try:
                    return int(float(n))
                except ValueError:
                    pass
        return 0

    # ─── プロフィール取得 ───

    def fetch_author_profile(self, username: str) -> Dict:
        """投稿者のプロフィールを取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        profile_url = f"https://www.threads.net/@{username}"
        logger.info("プロフィール取得: @%s", username)

        try:
            self._page.goto(profile_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("プロフィール読み込みタイムアウト: %s (続行)", e)

        profile = {
            'username': username,
            'display_name': '',
            'bio': '',
            'followers_count': None,
            'following_count': None,
            'is_verified': False,
            'profile_url': profile_url,
        }

        try:
            # 表示名
            title_el = self._page.query_selector('h1, h2, [data-testid="user-name"]')
            if title_el:
                profile['display_name'] = title_el.inner_text().strip()

            # 自己紹介
            bio_el = self._page.query_selector('meta[name="description"]')
            if bio_el:
                profile['bio'] = bio_el.get_attribute('content') or ''

            # フォロワー数
            page_text = self._page.content()
            followers_match = re.search(r'([\d,.]+[KkMm万]?)\s*(?:followers|フォロワー)', page_text)
            if followers_match:
                profile['followers_count'] = self._parse_count_text(followers_match.group(1))

            # 認証バッジ
            verified_el = self._page.query_selector('[data-testid="verified-badge"], svg[aria-label*="認証"]')
            if verified_el:
                profile['is_verified'] = True

        except Exception as e:
            logger.warning("プロフィール解析エラー @%s: %s", username, e)

        return profile

    # ─── 投稿者の過去投稿取得 ───

    def fetch_author_posts(self, username: str, max_scrolls: int = 10) -> List[Dict]:
        """投稿者の過去投稿をスクレイピングして取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        profile_url = f"https://www.threads.net/@{username}"
        logger.info("投稿履歴取得開始: @%s", username)

        try:
            self._page.goto(profile_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("ページ読み込みタイムアウト: %s (続行)", e)

        posts = []
        for i in range(max_scrolls):
            new_posts = self._extract_posts_from_page(keyword='')
            for p in new_posts:
                p['username'] = username
                if p not in posts:
                    posts.append(p)

            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(random.uniform(2, 5))
            new_height = self._page.evaluate('document.body.scrollHeight')
            if new_height == prev_height:
                break

        logger.info("投稿履歴取得完了: @%s → %d件", username, len(posts))
        return posts
