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


def _sanitize(text: str) -> str:
    """サロゲート文字を除去して安全な UTF-8 文字列を返す。
    Playwright が返す文字列に JavaScript の lone surrogate が含まれる場合がある。
    """
    if not isinstance(text, str):
        return str(text)
    return text.encode('utf-8', errors='replace').decode('utf-8')
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

    # フォロワー不明時のスコアベースバズ閾値
    SCORE_VIRAL_THRESHOLD = 1500   # likes×1 + replies×3 + reposts×2.5 >= 1500

    @classmethod
    def calc_engagement_rate(cls, post_data: Dict, followers: int) -> Optional[float]:
        """エンゲージメント率を算出。フォロワー不明時は None を返す。"""
        if not followers or followers <= 0:
            return None
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

        followers_known = followers is not None and followers > 0

        if followers_known:
            # フォロワー既知: 従来ロジック（いいね/リプライ閾値 + ER閾値）
            meets_likes = post_data.get('like_count', 0) >= threshold['min_likes']
            meets_replies = post_data.get('reply_count', 0) >= threshold['min_replies']
            meets_rate = engagement_rate >= threshold['engagement_rate']
            viral = (meets_likes or meets_replies) and meets_rate
        else:
            # フォロワー不明: スコアベースで判定
            viral = engagement_score >= cls.SCORE_VIRAL_THRESHOLD

        return {
            'is_viral': viral,
            'engagement_rate': round(engagement_rate, 2) if engagement_rate is not None else None,
            'engagement_score': round(engagement_score, 2),
            'tier': tier,
        }


# ─── 低品質リプライ判定 ───

# 絵文字判定用パターン（Emoji + 記号 + 空白のみ）
_EMOJI_ONLY_RE = re.compile(
    r'^[\s\u2600-\u27BF\U0001F300-\U0001FAFF\U0001F600-\U0001F64F'
    r'\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
    r'\U0001FA70-\U0001FAFF\u2702-\u27B0\uFE0F\u200D\u20E3'
    r'\u2934\u2935\u25AA-\u25FE\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55'
    r'\u3030\u303D\u3297\u3299\U000E0020-\U000E007F!\?\.\,\s]+$'
)


def _is_low_quality_reply(post_data: Dict) -> bool:
    """低品質リプライ判定。
    条件: いいね0 かつ リポスト0 かつ (テキスト50文字以下 or 絵文字のみ)
    """
    like_count = post_data.get('like_count', 0) or 0
    repost_count = post_data.get('repost_count', 0) or 0

    # エンゲージメントがあるなら除外しない
    if like_count > 0 or repost_count > 0:
        return False

    text = (post_data.get('text_content', '') or '').strip()

    # 絵文字のみ
    if _EMOJI_ONLY_RE.match(text):
        return True

    # 50文字以下の短文
    if len(text) <= 50:
        return True

    return False


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


# ─── インプレッション（表示回数）HTML フォールバック抽出 ───

def _parse_view_count_text(text: str) -> Optional[int]:
    """「1.2万回表示」「123,456 views」等のテキストからインプレッション数を抽出"""
    # 日本語: "1.2万回表示", "100万回表示", "1,234回表示"
    m = re.search(r'([\d,]+(?:\.\d+)?)\s*万\s*回\s*表示', text)
    if m:
        num_str = m.group(1).replace(',', '')
        try:
            return int(float(num_str) * 10000)
        except (ValueError, OverflowError):
            pass

    m = re.search(r'([\d,]+)\s*回\s*表示', text)
    if m:
        try:
            return int(m.group(1).replace(',', ''))
        except (ValueError, OverflowError):
            pass

    # 英語: "1.2M views", "123K views", "1,234 views"
    m = re.search(r'([\d,]+(?:\.\d+)?)\s*([MmKk])?\s*views', text, re.IGNORECASE)
    if m:
        num_str = m.group(1).replace(',', '')
        multiplier = 1
        suffix = (m.group(2) or '').upper()
        if suffix == 'M':
            multiplier = 1000000
        elif suffix == 'K':
            multiplier = 1000
        try:
            return int(float(num_str) * multiplier)
        except (ValueError, OverflowError):
            pass

    return None


# ─── メディア情報抽出ヘルパー ───

def _extract_best_image(image_versions: Optional[Dict]) -> Optional[Dict]:
    """image_versions2 オブジェクトから最大サイズの画像URLを取得"""
    if not image_versions or not isinstance(image_versions, dict):
        return None
    candidates = image_versions.get('candidates', [])
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.get('width', 0) * c.get('height', 0))
    url = best.get('url', '')
    if not url:
        return None
    return {
        'type': 'image',
        'url': url,
        'width': best.get('width', 0),
        'height': best.get('height', 0),
    }


def _extract_media_entry(media_item: Dict) -> Optional[Dict]:
    """carousel_media の個別アイテムからメディア情報を抽出"""
    video_versions = media_item.get('video_versions') or []
    image_versions = media_item.get('image_versions2')

    if video_versions:
        best = max(video_versions, key=lambda v: v.get('width', 0) * v.get('height', 0))
        return {
            'type': 'video',
            'url': best.get('url', ''),
            'width': best.get('width', 0),
            'height': best.get('height', 0),
        }
    if image_versions:
        return _extract_best_image(image_versions)
    return None


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

    # インプレッション（表示回数）抽出
    impressions = None
    # SSR JSON の様々なフィールド名を試行
    for field in ['view_count', 'play_count', 'impression_count', 'views',
                  'video_view_count', 'media_preview_like_count']:
        val = post.get(field)
        if val and isinstance(val, (int, float)) and val > 0:
            impressions = int(val)
            break
    # text_post_app_info 内も探索
    if impressions is None:
        for field in ['view_count', 'impression_count', 'views']:
            val = tpai.get(field)
            if val and isinstance(val, (int, float)) and val > 0:
                impressions = int(val)
                break

    # テキストベースのインプレッション抽出（"〇万回表示", "〇 views" 等）
    if impressions is None:
        # post / item 内の文字列フィールドを探索
        str_candidates = []
        for obj in [post, tpai, item or {}]:
            for v in obj.values():
                if isinstance(v, str) and ('表示' in v or 'view' in v.lower()):
                    str_candidates.append(v)
        for s in str_candidates:
            parsed_imp = _parse_view_count_text(s)
            if parsed_imp:
                impressions = parsed_imp
                break

    # デバッグ: impressions 関連の候補フィールドをログ（最初の数件のみ）
    if not hasattr(_parse_ssr_post, '_imp_debug_count'):
        _parse_ssr_post._imp_debug_count = 0
    if _parse_ssr_post._imp_debug_count < 3:
        imp_candidates = {k: v for k, v in post.items()
                         if isinstance(v, (int, float)) and k not in
                         ('like_count', 'taken_at', 'pk', 'id', 'original_width', 'original_height')}
        tpai_candidates = {k: v for k, v in tpai.items()
                          if isinstance(v, (int, float))}
        logger.info("[DEBUG] impressions候補 post数値: %s, tpai数値: %s",
                    json.dumps(imp_candidates, default=str)[:300],
                    json.dumps(tpai_candidates, default=str)[:200])
        _parse_ssr_post._imp_debug_count += 1

    # 固定ポスト判定
    is_pinned = False
    if item and isinstance(item, dict):
        is_pinned = bool(item.get('pinned') or item.get('is_pinned'))

    # ─── メディア（画像/動画）抽出 ───
    # Threads SSR JSON の media_type 値:
    #   1 = 画像投稿, 2 = 動画投稿, 8 = カルーセル, 19 = テキスト投稿
    # image_versions2 は全投稿に存在する（OGPサムネイル含む）ため単独では使用不可。
    # carousel_media / video_versions は信頼できるシグナル。
    # mt == 1 は画像投稿のシグナル（テキスト投稿は通常 mt == 19 or None）。
    media_type = 'text'
    media_urls = []

    mt = post.get('media_type')
    carousel_media = post.get('carousel_media') or []
    image_versions = post.get('image_versions2')
    video_versions = post.get('video_versions') or []

    # デバッグログ: media_type 値を記録（最初の数件）
    if not hasattr(_parse_ssr_post, '_media_debug_count'):
        _parse_ssr_post._media_debug_count = 0
    if _parse_ssr_post._media_debug_count < 10:
        ow = post.get('original_width', 0)
        oh = post.get('original_height', 0)
        has_iv = bool(image_versions)
        has_cm = bool(carousel_media)
        has_vv = bool(video_versions)
        logger.info(
            "[DEBUG] media判定: mt=%s, original=%sx%s, "
            "image_versions2=%s, carousel=%s, video=%s, text=%s",
            mt, ow, oh, has_iv, has_cm, has_vv,
            (text[:30] if text else ''),
        )
        _parse_ssr_post._media_debug_count += 1

    if carousel_media:
        media_type = 'carousel'
        for cm in carousel_media:
            cm_entry = _extract_media_entry(cm)
            if cm_entry:
                media_urls.append(cm_entry)
    elif video_versions or mt == 2:
        media_type = 'video'
        # 動画URL（最高画質を選択）
        if video_versions:
            best = max(video_versions, key=lambda v: v.get('width', 0) * v.get('height', 0))
            media_urls.append({
                'type': 'video',
                'url': best.get('url', ''),
                'width': best.get('width', 0),
                'height': best.get('height', 0),
            })
        # 動画のサムネイル画像
        if image_versions:
            img_entry = _extract_best_image(image_versions)
            if img_entry:
                img_entry['type'] = 'thumbnail'
                media_urls.append(img_entry)
    elif mt == 1:
        # media_type=1 は画像投稿（テキスト投稿は mt=19 or None）
        media_type = 'image'
        if image_versions:
            img_entry = _extract_best_image(image_versions)
            if img_entry:
                media_urls.append(img_entry)

    # post_url からメディアURL構築（フォールバック）
    if not media_urls and code and mt in (1, 2, 8):
        media_type = {1: 'image', 2: 'video', 8: 'carousel'}.get(mt, 'text')
        media_urls.append({
            'type': media_type,
            'url': f"{THREADS_BASE}/post/{code}/media",
            'width': post.get('original_width', 0),
            'height': post.get('original_height', 0),
        })

    # メディアURLをサニタイズ
    media_urls = [m for m in media_urls if m.get('url')]

    return {
        'text_content': text,
        'username': username,
        'display_name': display_name,
        'is_verified': is_verified,
        'like_count': like_count,
        'reply_count': reply_count,
        'repost_count': repost_count,
        'impressions': impressions,
        'post_url': post_url,
        'posted_at': posted_at,
        'is_pinned': is_pinned,
        'media_type': media_type,
        'media_urls': media_urls,
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
        self._response_handler = None
        self._captured_thread_data: List[str] = []

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

    # ─── API レスポンス傍受 ───

    def _start_response_capture(self):
        """スクロール時の GraphQL API レスポンスを傍受開始"""
        self._captured_thread_data = []

        def _on_response(response):
            try:
                url = response.url
                if '/api/' not in url and '/graphql' not in url:
                    return
                content_type = response.headers.get('content-type', '')
                if 'json' not in content_type and 'text' not in content_type:
                    return
                # response.text() はサロゲート文字でクラッシュするため body() から手動デコード
                try:
                    raw = response.body()
                    body = raw.decode('utf-8', errors='replace')
                except Exception:
                    return
                if '"thread_items"' in body:
                    self._captured_thread_data.append(body)
                    logger.info("[DEBUG] API レスポンス傍受: URL=%s, body長=%d",
                                _sanitize(url[:120]), len(body))
            except Exception as e:
                logger.warning("[DEBUG] レスポンス傍受エラー: %s", e)

        self._response_handler = _on_response
        self._page.on('response', self._response_handler)
        logger.info("[DEBUG] API レスポンス傍受を開始")

    def _stop_response_capture(self):
        """API レスポンス傍受を停止"""
        if self._response_handler:
            self._page.remove_listener('response', self._response_handler)
            self._response_handler = None
            logger.info("[DEBUG] API レスポンス傍受を停止")

    def _collect_captured_posts(self) -> List[Dict]:
        """傍受したレスポンスから投稿データを抽出してバッファをクリア"""
        posts = []
        for body in self._captured_thread_data:
            extracted = _extract_thread_items_from_html(body)
            posts.extend(extracted)
        resp_count = len(self._captured_thread_data)
        self._captured_thread_data.clear()
        if resp_count > 0:
            logger.info("[DEBUG] 傍受レスポンス %d件から %d投稿を抽出", resp_count, len(posts))
        return posts

    def close(self):
        self._stop_response_capture()
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

    def search_keyword(self, keyword: str, exclude_replies: bool = True, sort_order: str = 'recent') -> List[Dict]:
        """キーワードで Threads を検索し、投稿を取得
        sort_order: 'recent'=新しい順, 'default'=おすすめ順
        """
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        serp_type = 'recent' if sort_order == 'recent' else 'default'
        encoded = quote(keyword)
        search_url = f"{THREADS_BASE}/search?q={encoded}&serp_type={serp_type}"
        logger.info("検索開始: %s → %s", keyword, search_url)

        try:
            self._page.goto(search_url, wait_until='networkidle', timeout=30000)
            logger.info("ページ読み込み完了: %s", self._page.url)
        except Exception as e:
            logger.warning("ページ読み込みタイムアウト: %s (続行)", e)

        # デバッグ: ページの状態を詳細記録
        current_url = self._page.url
        html = _sanitize(self._page.content())
        title = _sanitize(self._page.title())
        logger.info("[DEBUG] 現在のURL: %s", current_url)
        logger.info("[DEBUG] ページタイトル: %s", title)
        logger.info("[DEBUG] HTML長: %d文字", len(html))

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
            with open(debug_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(f"URL: {current_url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"HTML Length: {len(html)}\n")
                f.write(f"thread_items count: {ti_count}\n")
                f.write("=" * 80 + "\n")
                f.write(html[:50000])
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

        # API レスポンス傍受を開始してスクロール
        self._start_response_capture()
        no_new_count = 0

        for i in range(ScraperConfig.MAX_SCROLL_COUNT):
            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            try:
                self._page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            time.sleep(random.uniform(3, 6))
            new_height = self._page.evaluate('document.body.scrollHeight')

            # 傍受した API レスポンスから投稿を抽出
            api_posts = self._collect_captured_posts()

            # SSR HTML からも抽出（フォールバック）
            html = _sanitize(self._page.content())
            html_posts = _extract_thread_items_from_html(html)

            all_new = api_posts + html_posts
            added = 0
            for p in all_new:
                key = p.get('post_url') or p.get('text_content', '')[:100]
                if key not in seen_urls:
                    seen_urls.add(key)
                    p['search_keyword'] = keyword
                    posts.append(p)
                    added += 1

            logger.info("スクロール #%d: 新規 %d件 (API=%d, HTML=%d) 累計 %d件",
                        i + 1, added, len(api_posts), len(html_posts), len(posts))

            if added == 0:
                no_new_count += 1
                if no_new_count >= 3 or (no_new_count >= 2 and new_height == prev_height):
                    logger.info("スクロール終了: 新規0が %d回連続 (height変化=%s)", no_new_count, new_height != prev_height)
                    break
            else:
                no_new_count = 0

        self._stop_response_capture()

        if exclude_replies:
            before = len(posts)
            posts = [p for p in posts if not _is_low_quality_reply(p)]
            filtered = before - len(posts)
            if filtered > 0:
                logger.info("低品質リプライ除外: %d件除外 → %d件残", filtered, len(posts))

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

        html = _sanitize(self._page.content())
        current_url = self._page.url
        title = _sanitize(self._page.title())
        logger.info("[DEBUG] プロフィールページ URL: %s", current_url)
        logger.info("[DEBUG] プロフィールページ タイトル: %s", title)
        logger.info("[DEBUG] プロフィールページ HTML長: %d文字", len(html))

        # ログインウォール/リダイレクトチェック
        if 'login' in current_url.lower() or 'login' in html[:3000].lower():
            logger.warning("[DEBUG] プロフィールページ: ログインウォールの可能性")

        profile = _extract_profile_from_html(html, username)
        logger.info("[DEBUG] プロフィール抽出結果: display_name=%s, followers=%s, following=%s",
                    profile.get('display_name'), profile.get('followers_count'), profile.get('following_count'))

        # 参加日を取得（モーダル経由）
        joined_at = self._extract_join_date()
        if joined_at:
            profile['joined_at'] = joined_at

        return profile

    # ─── 参加日取得 ───

    def _extract_join_date(self) -> Optional[str]:
        """
        プロフィールページから参加日を取得する。
        方法1: SSR JSON 内の date_joined / created_at フィールド
        方法2: 「...」→「このプロフィールについて」モーダル
        """
        # ── 方法1: SSR JSON から参加日フィールドを検索 ──
        try:
            html = _sanitize(self._page.content())
            for field in ['date_joined', 'created_at', 'joined']:
                pattern = rf'"{field}"\s*:\s*"([^"]+)"'
                m = re.search(pattern, html)
                if m:
                    logger.info("[DEBUG] 参加日: SSR JSON の %s から取得: %s", field, m.group(1))
                    return m.group(1)
        except Exception as e:
            logger.warning("[DEBUG] 参加日: SSR JSON 検索エラー: %s", e)

        # ── 方法2: モーダルから取得 ──
        try:
            # プロフィール付近の SVG アイコンボタン候補を全て取得し、
            # 順番にクリックして「このプロフィールについて」メニューが出るか確認
            about_keywords = ['このプロフィールについて', 'About this profile',
                              'About this account', 'プロフィールについて', 'アカウントについて']

            try:
                candidate_indices = self._page.evaluate("""() => {
                    const btns = document.querySelectorAll('[role="button"]');
                    const result = [];
                    for (let i = 0; i < btns.length; i++) {
                        const b = btns[i];
                        if (!b.querySelector('svg')) continue;
                        const rect = b.getBoundingClientRect();
                        if (rect.width > 50 || rect.height > 50) continue;
                        if (rect.width < 5 || rect.height < 5) continue;
                        const text = (b.textContent || '').trim();
                        if (text.length > 5) continue;
                        if (rect.top > 600) continue;
                        const aria = b.getAttribute('aria-label') || '';
                        // ナビメニュー除外
                        if (aria === 'もっと見る' || aria === 'More') continue;
                        result.push({idx: i, aria: aria, w: Math.round(rect.width),
                                     h: Math.round(rect.height), y: Math.round(rect.top)});
                    }
                    return result;
                }""")
                logger.info("[DEBUG] 参加日: SVG ボタン候補 %d件: %s",
                            len(candidate_indices),
                            json.dumps(candidate_indices, ensure_ascii=False)[:400])
            except Exception as e:
                logger.warning("[DEBUG] 参加日: JS ボタン検索エラー: %s", e)
                candidate_indices = []

            about_found = False
            for cand in candidate_indices:
                idx = cand['idx']
                try:
                    btn = self._page.locator('[role="button"]').nth(idx)
                    btn.click()
                    time.sleep(1.5)

                    # クリック後に「このプロフィールについて」が出るか確認
                    for kw in about_keywords:
                        try:
                            about_btn = self._page.get_by_text(kw, exact=False)
                            if about_btn.is_visible(timeout=1500):
                                about_btn.click()
                                about_found = True
                                logger.info("[DEBUG] 参加日: ボタン index=%d → '%s' をクリック", idx, kw)
                                break
                        except Exception:
                            continue

                    if about_found:
                        break

                    # 違うメニューだった場合: 内容をログして閉じる
                    try:
                        menu_text = self._page.evaluate("""() => {
                            const els = document.querySelectorAll(
                                '[role="dialog"], [role="menu"], [role="presentation"], [role="listbox"]'
                            );
                            const texts = [];
                            els.forEach(el => {
                                const t = (el.textContent || '').trim();
                                if (t) texts.push(t.slice(0, 100));
                            });
                            return texts;
                        }""")
                        logger.info("[DEBUG] 参加日: ボタン index=%d は別メニュー: %s",
                                    idx, json.dumps(menu_text, ensure_ascii=False)[:300])
                    except Exception:
                        pass
                    self._page.keyboard.press('Escape')
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning("[DEBUG] 参加日: ボタン index=%d クリックエラー: %s", idx, e)
                    try:
                        self._page.keyboard.press('Escape')
                        time.sleep(0.3)
                    except Exception:
                        pass

            if not about_found:
                # デバッグ: 全 role="button" 一覧
                try:
                    all_btns = self._page.evaluate("""() => {
                        const btns = document.querySelectorAll('[role="button"]');
                        return Array.from(btns).slice(0, 25).map((b, i) => {
                            const rect = b.getBoundingClientRect();
                            return {
                                idx: i, aria: b.getAttribute('aria-label') || '',
                                text: (b.textContent || '').slice(0, 30).trim(),
                                svg: !!b.querySelector('svg'),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                                y: Math.round(rect.top),
                            };
                        });
                    }""")
                    logger.warning("[DEBUG] 参加日: 全候補で失敗。role=button一覧: %s",
                                   json.dumps(all_btns, ensure_ascii=False)[:1000])
                except Exception:
                    pass
                return None

            time.sleep(2)

            # モーダルからテキストを取得
            page_html = _sanitize(self._page.content())

            # 「参加日」の後の日付を抽出（例: "2025年2月"）
            match = re.search(r'参加日.*?(\d{4}年\d{1,2}月)', page_html)
            if match:
                joined_at = match.group(1)
                logger.info("[DEBUG] 参加日抽出成功: %s", joined_at)
                self._page.keyboard.press('Escape')
                time.sleep(0.5)
                return joined_at

            # 英語フォールバック（"Joined February 2025"）
            match = re.search(r'Joined\s+(\w+\s+\d{4})', page_html)
            if match:
                joined_at = match.group(1)
                logger.info("[DEBUG] 参加日抽出成功(EN): %s", joined_at)
                self._page.keyboard.press('Escape')
                time.sleep(0.5)
                return joined_at

            logger.warning("[DEBUG] 参加日テキストがモーダル内に見つかりません")
            self._page.keyboard.press('Escape')
            time.sleep(0.5)

        except Exception as e:
            logger.warning("[DEBUG] 参加日取得エラー: %s", e)
            try:
                self._page.keyboard.press('Escape')
                time.sleep(0.5)
            except Exception:
                pass

        return None

    # ─── 投稿者の過去投稿取得 ───

    def fetch_author_posts(self, username: str, max_scrolls: int = 10, exclude_replies: bool = True) -> List[Dict]:
        """投稿者の過去投稿をスクレイピングして取得"""
        self._ensure_browser()
        self.rate_limiter.wait_if_needed()

        profile_url = f"{THREADS_BASE}/@{username}"
        logger.info("[DEBUG] 投稿履歴取得開始: @%s → %s", username, profile_url)

        try:
            self._page.goto(profile_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            logger.warning("[DEBUG] 投稿履歴ページ読み込みタイムアウト: %s (続行)", e)

        html = _sanitize(self._page.content())
        current_url = self._page.url
        title = _sanitize(self._page.title())
        logger.info("[DEBUG] 投稿履歴ページ URL: %s", current_url)
        logger.info("[DEBUG] 投稿履歴ページ タイトル: %s", title)
        logger.info("[DEBUG] 投稿履歴ページ HTML長: %d文字", len(html))

        ti_count = html.count('"thread_items"')
        logger.info("[DEBUG] 投稿履歴ページ thread_items 出現回数: %d", ti_count)

        # デバッグ用: HTML を一時ファイルに保存
        try:
            debug_path = '/app/deploy/debug_author_html.txt'
            with open(debug_path, 'w', encoding='utf-8', errors='replace') as f:
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

        # API レスポンス傍受を開始してスクロール
        self._start_response_capture()
        no_new_count = 0

        for i in range(max_scrolls):
            prev_height = self._page.evaluate('document.body.scrollHeight')
            self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            try:
                self._page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            time.sleep(random.uniform(3, 6))
            new_height = self._page.evaluate('document.body.scrollHeight')

            # 傍受した API レスポンスから投稿を抽出
            api_posts = self._collect_captured_posts()

            # SSR HTML からも抽出（フォールバック）
            html = _sanitize(self._page.content())
            html_posts = _extract_thread_items_from_html(html)

            all_new = api_posts + html_posts
            added = 0
            for p in all_new:
                p['username'] = username
                key = p.get('post_url') or p.get('text_content', '')[:100]
                if key not in seen_urls:
                    seen_urls.add(key)
                    posts.append(p)
                    added += 1

            logger.info("投稿履歴スクロール #%d: 新規 %d件 (API=%d, HTML=%d) 累計 %d件",
                        i + 1, added, len(api_posts), len(html_posts), len(posts))

            if added == 0:
                no_new_count += 1
                if no_new_count >= 3 or (no_new_count >= 2 and new_height == prev_height):
                    logger.info("スクロール終了: 新規0が %d回連続 (height変化=%s)", no_new_count, new_height != prev_height)
                    break
            else:
                no_new_count = 0

        self._stop_response_capture()

        if exclude_replies:
            before = len(posts)
            posts = [p for p in posts if not _is_low_quality_reply(p)]
            filtered = before - len(posts)
            if filtered > 0:
                logger.info("低品質リプライ除外: %d件除外 → %d件残", filtered, len(posts))

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
