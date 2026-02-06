# -*- coding: utf-8 -*-
"""
Threads バズ投稿スクレイパー
Playwright (stealth) を使用して Threads 検索結果をスクレイピングする。
ページソースに埋め込まれた SSR JSON データを抽出する方式。
Docker 環境では既にインストール済みの Chromium を使用する。
"""
import json
import logging
import os
import random
import re
import shutil
import time
from datetime import datetime, timezone as dt_timezone
from typing import Dict, List, Optional
from urllib.parse import quote

from django.utils import timezone

logger = logging.getLogger(__name__)

THREADS_BASE = "https://www.threads.com"
STORAGE_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'deploy', 'threads_session.json',
)


# ─── 設定 ───

class ScraperConfig:
    """スクレイピング設定"""
    MIN_DELAY = 3          # 最小待機秒数
    MAX_DELAY = 8          # 最大待機秒数
    REQUESTS_PER_HOUR = 60 # 1時間あたりの最大リクエスト数
    MAX_SCROLL_COUNT = 10  # 検索結果ページのスクロール回数
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

    # 保存済みセッションがあれば読み込む
    storage_state = None
    if os.path.exists(STORAGE_STATE_PATH):
        storage_state = STORAGE_STATE_PATH
        logger.info("セッションファイル読み込み: %s", STORAGE_STATE_PATH)
    else:
        logger.warning("セッションファイルなし: %s（未認証でアクセスします）", STORAGE_STATE_PATH)

    context = browser.new_context(
        viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
        user_agent=random.choice(ScraperConfig.USER_AGENTS),
        locale='ja-JP',
        timezone_id='Asia/Tokyo',
        storage_state=storage_state,
    )
    page = context.new_page()

    # webdriver プロパティを隠蔽
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    return pw, browser, context, page


# ─── SSR JSON 抽出 ───

def _extract_thread_items_from_html(html: str) -> List[Dict]:
    """ページ HTML から SSR 埋め込み JSON の thread_items を抽出して投稿データ一覧を返す"""
    posts = []

    matches = list(re.finditer(r'"thread_items":\[\{', html))
    logger.info("[DEBUG] _extract: thread_items 正規表現マッチ数: %d", len(matches))

    for idx, m in enumerate(matches):
        start = m.start()
        arr_start = html.index('[', start)
        depth = 0
        pos = arr_start
        end = min(len(html), arr_start + 20000)
        while pos < end:
            ch = html[pos]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    break
            elif ch == '\\':
                pos += 1
            pos += 1

        raw = html[arr_start:pos + 1]
        logger.info("[DEBUG] _extract: ブロック#%d raw長=%d", idx, len(raw))

        try:
            items = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[DEBUG] _extract: ブロック#%d JSON パース失敗: %s (先頭200文字: %s)", idx, e, raw[:200])
            continue

        logger.info("[DEBUG] _extract: ブロック#%d items数=%d", idx, len(items))

        for item in items:
            post_obj = item.get('post')
            if not post_obj:
                logger.info("[DEBUG] _extract: post キーなし (keys=%s)", list(item.keys())[:5])
                continue
            parsed = _parse_ssr_post(post_obj, item=item)
            if parsed and parsed.get('text_content'):
                posts.append(parsed)
            else:
                logger.info("[DEBUG] _extract: テキストなしでスキップ (username=%s)", post_obj.get('user', {}).get('username', '?'))

    logger.info("[DEBUG] _extract: 最終結果 %d件", len(posts))
    return posts


def _parse_ssr_post(post: Dict, item: Optional[Dict] = None) -> Optional[Dict]:
    """SSR JSON の post オブジェクトから必要なフィールドを抽出"""
    # テキスト取得: caption.text を優先、なければ text_fragments
    text = ''
    caption = post.get('caption')
    if caption and isinstance(caption, dict):
        text = caption.get('text', '')

    if not text:
        tpai = post.get('text_post_app_info', {})
        frags = tpai.get('text_fragments', {}).get('fragments', [])
        for f in frags:
            pt = f.get('plaintext', '')
            if pt:
                text += pt

    if not text:
        return None

    # ユーザー情報
    user = post.get('user', {})
    username = user.get('username', '')
    display_name = user.get('full_name', '')
    is_verified = user.get('is_verified', False)

    # エンゲージメント
    like_count = post.get('like_count', 0) or 0
    tpai = post.get('text_post_app_info', {})
    reply_count = tpai.get('direct_reply_count', 0) or 0
    repost_count = tpai.get('repost_count', 0) or 0

    # 投稿URL
    code = post.get('code', '')
    post_url = f"{THREADS_BASE}/post/{code}" if code else ''

    # 投稿日時
    taken_at = post.get('taken_at')
    posted_at = None
    if taken_at:
        try:
            posted_at = datetime.fromtimestamp(int(taken_at), tz=dt_timezone.utc)
        except (ValueError, OSError):
            pass

    # 固定ポスト判定
    is_pinned = False
    if item and isinstance(item, dict):
        is_pinned = bool(item.get('pinned') or item.get('is_pinned'))

    return {
        'text_content': text,
        'username': username,
        'display_name': display_name,
        'is_verified': is_verified,
        'like_count': like_count,
        'reply_count': reply_count,
        'repost_count': repost_count,
        'post_url': post_url,
        'posted_at': posted_at,
        'is_pinned': is_pinned,
    }


def _extract_profile_from_html(html: str, username: str) -> Dict:
    """ページ HTML からプロフィール情報を抽出"""
    profile = {
        'username': username,
        'display_name': '',
        'bio': '',
        'followers_count': None,
        'following_count': None,
        'is_verified': False,
        'profile_url': f"{THREADS_BASE}/@{username}",
    }

    # SSR JSON からユーザー情報を探す
    # "username":"<target>" の前後にプロフィールデータがある
    pattern = rf'"username":"{re.escape(username)}"'
    match = re.search(pattern, html)
    if not match:
        return profile

    # ユーザーオブジェクトを囲むブロックを広めに取得
    start = max(0, match.start() - 2000)
    end = min(len(html), match.end() + 5000)
    chunk = html[start:end]

    # full_name
    fn = re.search(r'"full_name":"((?:[^"\\]|\\.)*)"', chunk)
    if fn:
        try:
            profile['display_name'] = json.loads('"' + fn.group(1) + '"')
        except (json.JSONDecodeError, ValueError):
            profile['display_name'] = fn.group(1)

    # bio (biography)
    bio = re.search(r'"biography":"((?:[^"\\]|\\.)*)"', chunk)
    if bio:
        try:
            profile['bio'] = json.loads('"' + bio.group(1) + '"')
        except (json.JSONDecodeError, ValueError):
            profile['bio'] = bio.group(1)

    # follower_count
    fc = re.search(r'"follower_count":(\d+)', chunk)
    if fc:
        profile['followers_count'] = int(fc.group(1))

    # following_count
    fgc = re.search(r'"following_count":(\d+)', chunk)
    if fgc:
        profile['following_count'] = int(fgc.group(1))

    # is_verified
    iv = re.search(r'"is_verified":(true|false)', chunk)
    if iv:
        profile['is_verified'] = iv.group(1) == 'true'

    # meta description からの bio 取得（フォールバック）
    if not profile['bio']:
        meta = re.search(r'<meta\s+name="description"\s+content="((?:[^"\\]|\\.)*)"', html)
        if meta:
            profile['bio'] = meta.group(1)

    return profile


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
            logger.info("[DEBUG] ブラウザ起動開始 (headless=%s)", self.headless)
            try:
                self._pw, self._browser, self._context, self._page = (
                    _create_playwright_browser(self.headless)
                )
                logger.info("[DEBUG] ブラウザ起動成功")
            except Exception as e:
                logger.error("[DEBUG] ブラウザ起動失敗: %s", e, exc_info=True)
                raise

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

        encoded = quote(keyword)
        search_url = f"{THREADS_BASE}/search?q={encoded}&serp_type=default"
        logger.info("検索開始: %s → %s", keyword, search_url)

        try:
            self._page.goto(search_url, wait_until='networkidle', timeout=30000)
            logger.info("ページ読み込み完了: %s", self._page.url)
        except Exception as e:
            logger.warning("ページ読み込みタイムアウト: %s (続行)", e)

        # デバッグ: ページの状態を詳細記録
        current_url = self._page.url
        html = self._page.content()
        title = self._page.title()
        logger.info("[DEBUG] 現在のURL: %s", current_url)
        logger.info("[DEBUG] ページタイトル: %s", title)
        logger.info("[DEBUG] HTML長: %d文字", len(html))
        logger.info("[DEBUG] HTML先頭500文字: %s", html[:500].replace('\n', ' '))

        # thread_items の存在チェック
        ti_count = html.count('"thread_items"')
        logger.info("[DEBUG] thread_items 出現回数: %d", ti_count)

        # ログインウォール/ボット検出チェック
        if 'login' in html[:3000].lower() or 'log in' in html[:3000].lower():
            logger.warning("[DEBUG] ログインウォールの可能性あり")
        if 'challenge' in html[:5000].lower():
            logger.warning("[DEBUG] チャレンジ/CAPTCHA の可能性あり")

        # デバッグ用: HTML を一時ファイルに保存
        try:
            debug_path = '/app/deploy/debug_scraper_html.txt'
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {current_url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"HTML Length: {len(html)}\n")
                f.write(f"thread_items count: {ti_count}\n")
                f.write("=" * 80 + "\n")
                f.write(html[:50000])  # 先頭50KB
            logger.info("[DEBUG] HTML を %s に保存しました", debug_path)
        except Exception as e:
            logger.warning("[DEBUG] HTML 保存失敗: %s", e)

        # 初回のページソースから SSR JSON を抽出
        seen_urls = set()
        posts = []

        initial = _extract_thread_items_from_html(html)
        for p in initial:
            key = p.get('post_url') or p.get('text_content', '')[:100]
            if key not in seen_urls:
                seen_urls.add(key)
                p['search_keyword'] = keyword
                posts.append(p)

        logger.info("初回抽出: %d件", len(posts))

        # スクロールして追加データを取得
        for i in range(ScraperConfig.MAX_SCROLL_COUNT):
            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            try:
                self._page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            time.sleep(random.uniform(3, 6))
            new_height = self._page.evaluate('document.body.scrollHeight')

            html = self._page.content()
            new_posts = _extract_thread_items_from_html(html)
            added = 0
            for p in new_posts:
                key = p.get('post_url') or p.get('text_content', '')[:100]
                if key not in seen_urls:
                    seen_urls.add(key)
                    p['search_keyword'] = keyword
                    posts.append(p)
                    added += 1

            logger.info("スクロール #%d: 新規 %d件 (累計 %d件)", i + 1, added, len(posts))
            if new_height == prev_height and added == 0:
                break

        logger.info("検索完了: %s → %d件取得", keyword, len(posts))
        return posts

    # ─── プロフィール取得 ───

    def fetch_author_profile(self, username: str) -> Dict:
        """投稿者のプロフィールを取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        profile_url = f"{THREADS_BASE}/@{username}"
        logger.info("[DEBUG] プロフィール取得開始: @%s → %s", username, profile_url)

        try:
            self._page.goto(profile_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("[DEBUG] プロフィール読み込みタイムアウト: %s (続行)", e)

        html = self._page.content()
        current_url = self._page.url
        title = self._page.title()
        logger.info("[DEBUG] プロフィールページ URL: %s", current_url)
        logger.info("[DEBUG] プロフィールページ タイトル: %s", title)
        logger.info("[DEBUG] プロフィールページ HTML長: %d文字", len(html))

        # ログインウォール/リダイレクトチェック
        if 'login' in current_url.lower() or 'login' in html[:3000].lower():
            logger.warning("[DEBUG] プロフィールページ: ログインウォールの可能性")

        profile = _extract_profile_from_html(html, username)
        logger.info("[DEBUG] プロフィール抽出結果: display_name=%s, followers=%s, following=%s",
                    profile.get('display_name'), profile.get('followers_count'), profile.get('following_count'))
        return profile

    # ─── 投稿者の過去投稿取得 ───

    def fetch_author_posts(self, username: str, max_scrolls: int = 10) -> List[Dict]:
        """投稿者の過去投稿をスクレイピングして取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        profile_url = f"{THREADS_BASE}/@{username}"
        logger.info("[DEBUG] 投稿履歴取得開始: @%s → %s", username, profile_url)

        try:
            self._page.goto(profile_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("[DEBUG] 投稿履歴ページ読み込みタイムアウト: %s (続行)", e)

        html = self._page.content()
        current_url = self._page.url
        title = self._page.title()
        logger.info("[DEBUG] 投稿履歴ページ URL: %s", current_url)
        logger.info("[DEBUG] 投稿履歴ページ タイトル: %s", title)
        logger.info("[DEBUG] 投稿履歴ページ HTML長: %d文字", len(html))

        ti_count = html.count('"thread_items"')
        logger.info("[DEBUG] 投稿履歴ページ thread_items 出現回数: %d", ti_count)

        # デバッグ用: HTML を一時ファイルに保存
        try:
            debug_path = '/app/deploy/debug_author_html.txt'
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {current_url}\nTitle: {title}\nHTML Length: {len(html)}\n")
                f.write(f"thread_items count: {ti_count}\n")
                f.write("=" * 80 + "\n")
                f.write(html[:50000])
            logger.info("[DEBUG] 投稿履歴 HTML を %s に保存", debug_path)
        except Exception as e:
            logger.warning("[DEBUG] HTML 保存失敗: %s", e)

        seen_urls = set()
        posts = []

        initial = _extract_thread_items_from_html(html)
        logger.info("[DEBUG] 投稿履歴 初回抽出: %d件", len(initial))
        for p in initial:
            p['username'] = username
            key = p.get('post_url') or p.get('text_content', '')[:100]
            if key not in seen_urls:
                seen_urls.add(key)
                posts.append(p)

        for i in range(max_scrolls):
            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            try:
                self._page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            time.sleep(random.uniform(3, 6))
            new_height = self._page.evaluate('document.body.scrollHeight')

            html = self._page.content()
            new_posts = _extract_thread_items_from_html(html)
            added = 0
            for p in new_posts:
                p['username'] = username
                key = p.get('post_url') or p.get('text_content', '')[:100]
                if key not in seen_urls:
                    seen_urls.add(key)
                    posts.append(p)
                    added += 1

            logger.info("投稿履歴スクロール #%d: 新規 %d件 (累計 %d件)", i + 1, added, len(posts))
            if new_height == prev_height and added == 0:
                break

        logger.info("投稿履歴取得完了: @%s → %d件", username, len(posts))
        return posts


# ─── Cookie 有効期限チェック ───

def check_session_validity() -> Dict:
    """
    保存済みセッション (threads_session.json) の Cookie 有効期限を確認する。
    戻り値: {'valid': bool, 'message': str, 'expires_at': datetime|None}
    """
    if not os.path.exists(STORAGE_STATE_PATH):
        return {
            'valid': False,
            'message': 'セッションファイルが見つかりません',
            'expires_at': None,
        }

    try:
        with open(STORAGE_STATE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {
            'valid': False,
            'message': f'セッションファイルの読み込みに失敗: {e}',
            'expires_at': None,
        }

    cookies = data.get('cookies', [])
    target_names = {'sessionid', 'ds_user_id'}
    earliest_expires = None

    for cookie in cookies:
        name = cookie.get('name', '')
        if name not in target_names:
            continue
        expires = cookie.get('expires')
        if expires and expires > 0:
            try:
                exp_dt = datetime.fromtimestamp(expires, tz=dt_timezone.utc)
                if earliest_expires is None or exp_dt < earliest_expires:
                    earliest_expires = exp_dt
            except (ValueError, OSError):
                pass

    if earliest_expires is None:
        return {
            'valid': False,
            'message': 'セッション Cookie (sessionid/ds_user_id) が見つかりません',
            'expires_at': None,
        }

    now = datetime.now(tz=dt_timezone.utc)
    if earliest_expires <= now:
        return {
            'valid': False,
            'message': f'セッション Cookie の有効期限が切れています ({earliest_expires.strftime("%Y/%m/%d %H:%M")} UTC)',
            'expires_at': earliest_expires,
        }

    remaining = earliest_expires - now
    days = remaining.days
    if days <= 3:
        return {
            'valid': True,
            'message': f'セッション Cookie の有効期限が残り{days}日です ({earliest_expires.strftime("%Y/%m/%d %H:%M")} UTC)',
            'expires_at': earliest_expires,
        }

    return {
        'valid': True,
        'message': f'セッション有効 (期限: {earliest_expires.strftime("%Y/%m/%d %H:%M")} UTC, 残り{days}日)',
        'expires_at': earliest_expires,
    }
