# -*- coding: utf-8 -*-
"""
Phase G スクレイパ設定層。

ResearchAccount.status に応じて使用するレートプロファイルを切り替える。
すべての値は環境変数で個別にオーバーライド可能。

ステータス別の既定値:
  VPS_WARMUP : 5 req/h、待機 60〜180s、深夜停止 22:00〜09:00、日次 30 req、スクロール 3 回
  ACTIVE     : 15 req/h、待機 15〜45s、深夜停止 02:00〜06:00、日次 200 req、スクロール 10 回
"""
import math
import os
import random
from datetime import time as _time
from typing import Dict, Optional, Tuple

from django.utils import timezone


# ─── 環境変数ヘルパー ───

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, '') else default
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    return raw if raw not in (None, '') else default


# ─── レートプロファイル ───

def _profile_warmup() -> Dict:
    return {
        'name': 'VPS_WARMUP',
        'requests_per_hour': _env_int('SCRAPER_WARMUP_REQUESTS_PER_HOUR', 5),
        'min_delay_sec':     _env_int('SCRAPER_WARMUP_MIN_DELAY_SEC', 60),
        'max_delay_sec':     _env_int('SCRAPER_WARMUP_MAX_DELAY_SEC', 180),
        'daily_limit':       _env_int('SCRAPER_WARMUP_DAILY_LIMIT', 30),
        'max_scroll_count':  _env_int('SCRAPER_WARMUP_MAX_SCROLL_COUNT', 3),
        'quiet_hours':       _env_str('SCRAPER_WARMUP_QUIET_HOURS', '22:00-09:00'),
    }


def _profile_active() -> Dict:
    return {
        'name': 'ACTIVE',
        'requests_per_hour': _env_int('SCRAPER_REQUESTS_PER_HOUR', 15),
        'min_delay_sec':     _env_int('SCRAPER_MIN_DELAY_SEC', 15),
        'max_delay_sec':     _env_int('SCRAPER_MAX_DELAY_SEC', 45),
        'daily_limit':       _env_int('SCRAPER_DAILY_LIMIT', 200),
        'max_scroll_count':  _env_int('SCRAPER_MAX_SCROLL_COUNT', 10),
        'quiet_hours':       _env_str('SCRAPER_QUIET_HOURS', '02:00-06:00'),
    }


def get_profile(status: str) -> Dict:
    """ResearchAccount.status から運用プロファイルを取得。
    NEW/SUSPENDED は呼び出し側で is_available チェック必須（保険として ACTIVE を返す）。
    """
    if status == 'VPS_WARMUP':
        return _profile_warmup()
    return _profile_active()


# ─── User-Agent プール（実機由来の代表的な UA を約 15 種） ───

USER_AGENTS = [
    # Windows Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    # macOS Chrome / Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    # Linux Chrome
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    # Edge
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.66',
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0',
]


def pick_user_agent() -> str:
    return random.choice(USER_AGENTS)


# ─── 深夜停止判定 ───

def parse_quiet_hours(text: str) -> Optional[Tuple[_time, _time]]:
    """'02:00-06:00' 等を (start, end) に。深夜跨ぎ（'22:00-09:00'）も対応。"""
    if not text:
        return None
    try:
        a, b = text.split('-')
        s_h, s_m = (int(x) for x in a.strip().split(':'))
        e_h, e_m = (int(x) for x in b.strip().split(':'))
        return (_time(s_h, s_m), _time(e_h, e_m))
    except Exception:
        return None


def is_in_quiet_hours(profile: Dict, now=None) -> bool:
    """現在時刻が profile['quiet_hours'] の停止帯にあるか（タイムゾーンは settings.TIME_ZONE）"""
    if now is None:
        now = timezone.localtime()
    rng = parse_quiet_hours(profile.get('quiet_hours', ''))
    if not rng:
        return False
    start, end = rng
    cur = now.time()
    if start <= end:
        return start <= cur < end
    # 跨ぎ
    return cur >= start or cur < end


# ─── 待機秒数（対数正規分布）───

def pick_delay_seconds(profile: Dict) -> float:
    """min〜max の対数正規分布で待機秒数を決定。
    中央値 ≒ (min+max)/2、σ_ln=0.4、上下限でクリップ。
    """
    mn = max(0.5, float(profile.get('min_delay_sec', 1)))
    mx = max(mn, float(profile.get('max_delay_sec', mn)))
    if mx <= mn:
        return mn
    median = (mn + mx) / 2.0
    sigma_ln = 0.4
    try:
        mu_ln = math.log(median)
        val = random.lognormvariate(mu_ln, sigma_ln)
    except (ValueError, OverflowError):
        val = random.uniform(mn, mx)
    return max(mn, min(mx, val))


# ─── プロキシ URL ───

def get_proxy_url() -> str:
    """環境変数 RESEARCH_PROXY_URL を返す。未設定なら空文字。"""
    return _env_str('RESEARCH_PROXY_URL', '')


def require_proxy_url() -> str:
    """プロキシ URL を取得。未設定なら RuntimeError。
    VPS 生 IP での Threads アクセス禁止（Phase G 設計原則）を強制する。
    """
    url = get_proxy_url()
    if not url:
        raise RuntimeError(
            'RESEARCH_PROXY_URL が未設定です。Phase G の設計原則として、'
            'プロキシ未設定で Threads にアクセスすることは禁止されています。'
            'VPS の .env に RESEARCH_PROXY_URL を設定してください。'
        )
    return url
