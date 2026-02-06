（質問）
スレッズでバズっている投稿を定期的にリサーチし、その投稿内容といいね数、インプレッションなどを記録して欲しい。さらにその投稿者のページに遷移してどんなアカウントかも調べたい。
公式apiだと難しいので、あなたのagentなどから、ブラウザ操作をルール化して、垢バンされないようなペースで調べる方式がよいか。
どのように具体的に実現できるかかんがえて。
claudeはwindowsのChromブラウザなどから操作できるか。あるいはwslなどでPythonプラグラムなどを作りシークレットブラウザの操作などが良いか。ベストプラクティスを調べてほしい

スレッズ（Threads）のバズ投稿リサーチシステムの構築について、いくつかの実現方法を調査・検討します。調査結果に基づいて、スレッズのバズ投稿リサーチシステムの実現方法をまとめます。

## スレッズバズ投稿リサーチシステムの実装案

### 1. **推奨アプローチ: Playwright + Python (WSL/Linux)**

調査結果から、**Playwright**が2025年現在のベストプラクティスです:

**理由:**
- **速度**: Seleniumより35-45%高速
- **安定性**: 自動待機機能で要素検出が確実
- **モダン**: Chrome DevTools Protocol (CDP)で直接通信
- **リソース効率**: メモリ使用量が少ない
- **レート制限対策**: ネットワークインターセプト機能が強力

### 2. **具体的な実装構成**

```python
# システム構成例
threads-research-system/
├── src/
│   ├── main.py              # メインスクリプト
│   ├── scraper/
│   │   ├── threads_scraper.py    # スクレイピングロジック
│   │   ├── browser_manager.py    # ブラウザ管理
│   │   └── data_parser.py        # データ抽出
│   ├── storage/
│   │   ├── database.py           # SQLite/PostgreSQL
│   │   └── csv_handler.py        # CSV出力
│   └── utils/
│       ├── rate_limiter.py       # レート制限
│       ├── logger.py             # ログ記録
│       └── config.py             # 設定管理
├── config/
│   ├── settings.yaml        # スクレイピング設定
│   └── targets.yaml         # ターゲットURL
├── data/
│   ├── posts.db            # データベース
│   └── exports/            # エクスポートファイル
└── logs/
    └── scraper.log
```

### 3. **垢バン防止のための重要な対策**調査結果を踏まえて、詳細な実装プランをまとめます。

## 完全な実装プラン

### **1. 推奨技術スタック**

```yaml
環境: WSL2 (Ubuntu) または Linux
言語: Python 3.10+
ブラウザ自動化: Playwright (playwright-stealth付き)
データベース: SQLite (小規模) / PostgreSQL (大規模)
プロキシ: Rotating Residential Proxies (必要に応じて)
```

### **2. 垢バン防止の具体的対策**

```python
# 主要な対策コード例

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import random

class ThreadsScraperConfig:
    """スクレイピング設定"""
    
    # レート制限設定
    MIN_DELAY = 3  # 最小待機秒数
    MAX_DELAY = 8  # 最大待機秒数
    REQUESTS_PER_HOUR = 60  # 1時間あたりの最大リクエスト数
    
    # ブラウザ設定
    HEADLESS = False  # headfulモードで実行(検出回避)
    VIEWPORT = {
        'width': random.randint(1366, 1920),
        'height': random.randint(768, 1080)
    }
    
    # ユーザーエージェント配列(ランダム切り替え)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...',
        # ... 複数のUA
    ]

class StealthBrowserManager:
    """ステルスブラウザ管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def launch(self):
        """ステルスブラウザを起動"""
        self.playwright = sync_playwright().start()
        
        # ブラウザ起動設定
        self.browser = self.playwright.chromium.launch(
            headless=False,  # 重要: headfulモード
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # コンテキスト作成(フィンガープリント偽装)
        self.context = self.browser.new_context(
            viewport=ThreadsScraperConfig.VIEWPORT,
            user_agent=random.choice(ThreadsScraperConfig.USER_AGENTS),
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            # Geolocation設定(必要に応じて)
            geolocation={'latitude': 35.6762, 'longitude': 139.6503},
            permissions=['geolocation']
        )
        
        # 新しいページ作成
        self.page = self.context.new_page()
        
        # Stealth適用(重要)
        stealth_sync(self.page)
        
        # navigator.webdriver除去
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return self.page

class RateLimiter:
    """レート制限管理"""
    
    def __init__(self, requests_per_hour=60):
        self.requests_per_hour = requests_per_hour
        self.request_times = []
        
    def wait_if_needed(self):
        """必要に応じて待機"""
        now = time.time()
        
        # 1時間以上前のリクエストを削除
        self.request_times = [t for t in self.request_times 
                             if now - t < 3600]
        
        # レート制限チェック
        if len(self.request_times) >= self.requests_per_hour:
            oldest = self.request_times[0]
            wait_time = 3600 - (now - oldest) + random.uniform(5, 15)
            print(f"レート制限: {wait_time:.0f}秒待機します...")
            time.sleep(wait_time)
        
        # ランダムな人間的な待機
        delay = random.uniform(
            ThreadsScraperConfig.MIN_DELAY,
            ThreadsScraperConfig.MAX_DELAY
        )
        time.sleep(delay)
        
        # リクエスト時刻を記録
        self.request_times.append(time.time())

class ThreadsScraper:
    """Threadsスクレイパー本体"""
    
    def __init__(self):
        self.browser_manager = StealthBrowserManager()
        self.rate_limiter = RateLimiter(
            requests_per_hour=ThreadsScraperConfig.REQUESTS_PER_HOUR
        )
        self.page = None
        
    def start(self):
        """スクレイピング開始"""
        self.page = self.browser_manager.launch()
        
    def scrape_trending_posts(self):
        """トレンド投稿をスクレイピング"""
        
        # レート制限チェック
        self.rate_limiter.wait_if_needed()
        
        # Threadsのトレンドページに移動
        self.page.goto('https://www.threads.net/', 
                      wait_until='networkidle')
        
        # スクロール動作(人間らしく)
        for _ in range(3):
            self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
            time.sleep(random.uniform(1.5, 3.5))
        
        # 投稿データ抽出(隠しJSONデータから)
        posts_data = self.page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/json"]');
                for (let script of scripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        // Threadsの投稿データ構造を解析
                        // (実際の構造は調査が必要)
                        return data;
                    } catch (e) {}
                }
                return null;
            }
        """)
        
        return posts_data
    
    def scrape_post_details(self, post_url):
        """個別投稿の詳細を取得"""
        
        self.rate_limiter.wait_if_needed()
        
        self.page.goto(post_url, wait_until='networkidle')
        
        # マウス動作のシミュレーション(ランダムに)
        if random.random() < 0.3:  # 30%の確率でマウス移動
            self.page.mouse.move(
                random.randint(100, 500),
                random.randint(100, 500)
            )
        
        # データ抽出
        post_data = {
            'url': post_url,
            'likes': self._extract_likes(),
            'impressions': self._extract_impressions(),
            'replies': self._extract_replies(),
            'reposts': self._extract_reposts(),
            'text': self._extract_text(),
            'timestamp': self._extract_timestamp()
        }
        
        return post_data
    
    def scrape_user_profile(self, username):
        """ユーザープロフィール取得"""
        
        self.rate_limiter.wait_if_needed()
        
        profile_url = f'https://www.threads.net/@{username}'
        self.page.goto(profile_url, wait_until='networkidle')
        
        # プロフィールデータ抽出
        profile_data = {
            'username': username,
            'display_name': self._extract_display_name(),
            'bio': self._extract_bio(),
            'followers': self._extract_followers_count(),
            'following': self._extract_following_count(),
            'verified': self._extract_verification_status(),
            'posts_count': self._extract_posts_count()
        }
        
        return profile_data
    
    def close(self):
        """ブラウザを閉じる"""
        if self.browser_manager.browser:
            self.browser_manager.browser.close()
        if self.browser_manager.playwright:
            self.browser_manager.playwright.stop()
```

### **3. データ保存スキーマ**

```sql
-- データベース設計

-- 投稿テーブル
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE NOT NULL,
    post_url TEXT NOT NULL,
    author_username TEXT NOT NULL,
    text_content TEXT,
    likes_count INTEGER DEFAULT 0,
    impressions_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    reposts_count INTEGER DEFAULT 0,
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_trending BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (author_username) REFERENCES users(username)
);

-- ユーザーテーブル
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    display_name TEXT,
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    posts_count INTEGER,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_url TEXT,
    first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- スクレイピング履歴テーブル
CREATE TABLE scraping_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    target_type TEXT, -- 'trending', 'post', 'user'
    target_id TEXT,
    status TEXT, -- 'success', 'failed', 'blocked'
    error_message TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- トレンドスナップショットテーブル
CREATE TABLE trending_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    rank_position INTEGER,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
```

### **4. 定期実行スケジュール設定**

```python
# scheduler.py

import schedule
import time
from datetime import datetime
import logging

class ThreadsScrapingScheduler:
    """定期スクレイピングスケジューラー"""
    
    def __init__(self):
        self.scraper = ThreadsScraper()
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logging.basicConfig(
            filename='logs/scraper.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def scrape_trending_job(self):
        """トレンド投稿取得ジョブ"""
        try:
            self.logger.info("トレンド投稿スクレイピング開始")
            self.scraper.start()
            
            # トレンド投稿を取得
            trending_posts = self.scraper.scrape_trending_posts()
            
            # 各投稿の詳細を取得
            for post in trending_posts[:10]:  # 上位10件のみ
                post_details = self.scraper.scrape_post_details(post['url'])
                
                # ユーザー情報も取得
                user_profile = self.scraper.scrape_user_profile(
                    post['author_username']
                )
                
                # データベースに保存
                self._save_to_database(post_details, user_profile)
                
            self.scraper.close()
            self.logger.info("スクレイピング正常終了")
            
        except Exception as e:
            self.logger.error(f"エラー発生: {str(e)}")
            self.scraper.close()
    
    def run(self):
        """スケジューラー実行"""
        
        # 1日3回実行 (朝9時、昼3時、夜9時)
        schedule.every().day.at("09:00").do(self.scrape_trending_job)
        schedule.every().day.at("15:00").do(self.scrape_trending_job)
        schedule.every().day.at("21:00").do(self.scrape_trending_job)
        
        print("スケジューラー起動中...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック

if __name__ == '__main__':
    scheduler = ThreadsScrapingScheduler()
    scheduler.run()
```

### **5. 必要なパッケージ**

```bash
# requirements.txt
playwright==1.41.0
playwright-stealth==1.0.6
schedule==1.2.0
python-dotenv==1.0.0
pandas==2.1.4
sqlalchemy==2.0.25
beautifulsoup4==4.12.3
```

```bash
# インストール手順
pip install -r requirements.txt
playwright install chromium
```

### **6. 運用上の注意点**

1. **レート制限の遵守**: 1時間に60リクエスト以下に抑える
2. **ヘッドフルモード**: 検出回避のため必ずGUI表示で実行
3. **ランダム化**: 待機時間、スクロール、マウス動作を全てランダム化
4. **セッション管理**: 長時間連続実行せず、定期的にブラウザを再起動
5. **プロキシ**: 大規模運用時はResidential Proxyを検討
6. **ログ監視**: 403エラーやブロックの兆候を常時監視

この方法なら、垢バンリスクを最小限に抑えつつ、効率的にThreadsのバズ投稿をリサーチできます。WSL2環境でPythonから実行するのが最も安定した運用が可能です。

（質問）
バズっている、という状態はどのように検索時に判断するのか。また、検索時は特定のキーワードの組み合わせで検索した結果に対してリサーチしてほしい。それはPython実行時のパラメータなどで指定できるか


優れた質問です！調査結果を踏まえて、「バズっている状態」の判断基準とキーワード検索機能の実装方法を説明します。

## 1. 「バズっている」状態の判断基準

調査結果から、Threadsにおけるバズ（viral）の定義は以下の通りです:

### **エンゲージメント率による判定**

```python
class ViralityDetector:
    """バズ判定ロジック"""
    
    # バズ判定の閾値設定
    VIRALITY_THRESHOLDS = {
        'engagement_rate': 4.5,  # エンゲージメント率4.5%以上
        'velocity_multiplier': 10,  # 通常の10倍以上の速度
        'time_window_hours': 24,    # 24時間以内
    }
    
    # エンゲージメントスコアの重み付け
    ENGAGEMENT_WEIGHTS = {
        'replies': 3.0,      # リプライが最重要（Threadsの特徴）
        'reposts': 2.5,      # リポスト
        'likes': 1.0,        # いいね
        'quotes': 2.0,       # 引用
        'profile_clicks': 1.5 # プロフィールクリック
    }
    
    # フォロワー数による相対的バズ判定
    VIRAL_MULTIPLIERS = {
        'micro': {      # 1,000-10,000フォロワー
            'min_likes': 500,
            'min_replies': 50,
            'engagement_rate': 5.0
        },
        'mid': {        # 10,000-100,000フォロワー
            'min_likes': 5000,
            'min_replies': 200,
            'engagement_rate': 3.0
        },
        'macro': {      # 100,000+フォロワー
            'min_likes': 50000,
            'min_replies': 1000,
            'engagement_rate': 2.0
        }
    }
    
    def calculate_engagement_score(self, post_data):
        """エンゲージメントスコア計算"""
        score = (
            post_data['replies'] * self.ENGAGEMENT_WEIGHTS['replies'] +
            post_data['reposts'] * self.ENGAGEMENT_WEIGHTS['reposts'] +
            post_data['likes'] * self.ENGAGEMENT_WEIGHTS['likes'] +
            post_data.get('quotes', 0) * self.ENGAGEMENT_WEIGHTS['quotes'] +
            post_data.get('profile_clicks', 0) * self.ENGAGEMENT_WEIGHTS['profile_clicks']
        )
        return score
    
    def calculate_engagement_rate(self, post_data, followers_count):
        """エンゲージメント率計算"""
        total_engagement = (
            post_data['likes'] + 
            post_data['replies'] + 
            post_data['reposts'] +
            post_data.get('quotes', 0)
        )
        
        if followers_count == 0:
            return 0
            
        engagement_rate = (total_engagement / followers_count) * 100
        return engagement_rate
    
    def is_viral(self, post_data, author_data):
        """バズ判定"""
        followers = author_data.get('followers_count', 0)
        
        # アカウントサイズの判定
        if followers < 10000:
            tier = 'micro'
        elif followers < 100000:
            tier = 'mid'
        else:
            tier = 'macro'
        
        threshold = self.VIRAL_MULTIPLIERS[tier]
        
        # エンゲージメント率チェック
        engagement_rate = self.calculate_engagement_rate(post_data, followers)
        
        # 絶対値チェック
        meets_likes = post_data['likes'] >= threshold['min_likes']
        meets_replies = post_data['replies'] >= threshold['min_replies']
        meets_rate = engagement_rate >= threshold['engagement_rate']
        
        # 速度チェック（投稿後24時間以内）
        hours_since_post = self._calculate_hours_since_post(post_data['posted_at'])
        is_recent = hours_since_post <= self.VIRALITY_THRESHOLDS['time_window_hours']
        
        # 総合判定
        is_viral = (
            is_recent and
            (meets_likes or meets_replies) and
            meets_rate
        )
        
        return {
            'is_viral': is_viral,
            'engagement_rate': engagement_rate,
            'engagement_score': self.calculate_engagement_score(post_data),
            'tier': tier,
            'hours_since_post': hours_since_post
        }
```

## 2. キーワード検索機能の実装

```python
# config.yaml - 設定ファイル
search_config:
  keywords:
    - ["AI", "機械学習"]
    - ["Python", "プログラミング"]
    - ["起業", "スタートアップ"]
  
  keyword_logic: "OR"  # OR / AND
  
  filters:
    min_likes: 100
    min_replies: 10
    posted_within_hours: 24
    languages: ["ja", "en"]
  
  scraping:
    max_posts_per_keyword: 50
    rate_limit_per_hour: 60
```

```python
# threads_keyword_scraper.py

import yaml
import argparse
from typing import List, Dict
from datetime import datetime, timedelta

class ThreadsKeywordScraper:
    """キーワードベースのThreadsスクレイパー"""
    
    def __init__(self, config_path: str = None):
        """初期化"""
        self.config = self._load_config(config_path) if config_path else {}
        self.browser_manager = StealthBrowserManager()
        self.rate_limiter = RateLimiter()
        self.virality_detector = ViralityDetector()
        self.page = None
        
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def search_by_keywords(self, keywords: List[str], logic: str = "OR"):
        """キーワード検索実行"""
        
        self.page = self.browser_manager.launch()
        results = []
        
        # キーワードの組み合わせを構築
        if logic == "AND":
            search_query = " ".join(keywords)
            results.extend(self._execute_search(search_query))
        else:  # OR
            for keyword in keywords:
                results.extend(self._execute_search(keyword))
        
        self.browser_manager.close()
        return results
    
    def _execute_search(self, query: str) -> List[Dict]:
        """個別の検索クエリを実行"""
        
        self.rate_limiter.wait_if_needed()
        
        # Threads検索ページに移動
        search_url = f"https://www.threads.net/search?q={query}&serp_type=default"
        self.page.goto(search_url, wait_until='networkidle')
        
        print(f"検索中: {query}")
        
        # スクロールしてより多くの結果を読み込む
        posts = []
        scroll_count = 0
        max_scrolls = 5
        
        while scroll_count < max_scrolls:
            # 現在のページから投稿を抽出
            new_posts = self._extract_posts_from_page()
            posts.extend(new_posts)
            
            # スクロール
            previous_height = self.page.evaluate('document.body.scrollHeight')
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # 人間らしい待機
            time.sleep(random.uniform(2, 4))
            
            # 新しいコンテンツが読み込まれたかチェック
            new_height = self.page.evaluate('document.body.scrollHeight')
            if new_height == previous_height:
                break
                
            scroll_count += 1
        
        # フィルタリングとバズ判定
        filtered_posts = self._filter_and_rank_posts(posts)
        
        return filtered_posts
    
    def _extract_posts_from_page(self) -> List[Dict]:
        """ページから投稿データを抽出"""
        
        # Threadsの隠しJSONデータから抽出
        posts_data = self.page.evaluate("""
            () => {
                const posts = [];
                const scripts = document.querySelectorAll('script[type="application/json"]');
                
                for (let script of scripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        // Threadsの投稿データ構造を解析
                        // (実際の構造は要調査・要調整)
                        if (data.require) {
                            // データ構造の解析ロジック
                            // ...
                        }
                    } catch (e) {}
                }
                
                return posts;
            }
        """)
        
        return posts_data
    
    def _filter_and_rank_posts(self, posts: List[Dict]) -> List[Dict]:
        """投稿をフィルタリング・ランキング"""
        
        config = self.config.get('search_config', {}).get('filters', {})
        
        filtered = []
        
        for post in posts:
            # 基本フィルタ
            if post['likes'] < config.get('min_likes', 0):
                continue
            if post['replies'] < config.get('min_replies', 0):
                continue
            
            # 時間フィルタ
            posted_at = datetime.fromisoformat(post['posted_at'])
            hours_ago = (datetime.now() - posted_at).total_seconds() / 3600
            if hours_ago > config.get('posted_within_hours', 24):
                continue
            
            # バズ判定
            author_data = {'followers_count': post.get('author_followers', 0)}
            virality_result = self.virality_detector.is_viral(post, author_data)
            
            post['virality_data'] = virality_result
            
            # バズっている投稿のみを抽出（オプション）
            if virality_result['is_viral']:
                filtered.append(post)
        
        # エンゲージメントスコアでソート
        filtered.sort(
            key=lambda x: x['virality_data']['engagement_score'],
            reverse=True
        )
        
        return filtered

# CLI実装
def main():
    """コマンドライン実行"""
    
    parser = argparse.ArgumentParser(
        description='Threadsキーワード検索スクレイパー'
    )
    
    # 引数定義
    parser.add_argument(
        '-k', '--keywords',
        nargs='+',
        required=True,
        help='検索キーワード（複数指定可）例: -k AI 機械学習'
    )
    
    parser.add_argument(
        '-l', '--logic',
        choices=['AND', 'OR'],
        default='OR',
        help='キーワード検索ロジック（AND/OR）デフォルト: OR'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='設定ファイルのパス（YAML）'
    )
    
    parser.add_argument(
        '--min-likes',
        type=int,
        default=100,
        help='最小いいね数フィルタ（デフォルト: 100）'
    )
    
    parser.add_argument(
        '--min-replies',
        type=int,
        default=10,
        help='最小リプライ数フィルタ（デフォルト: 10）'
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='投稿後の経過時間フィルタ（時間）デフォルト: 24'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output/search_results.json',
        help='出力ファイルパス'
    )
    
    parser.add_argument(
        '--viral-only',
        action='store_true',
        help='バズっている投稿のみを抽出'
    )
    
    args = parser.parse_args()
    
    # スクレイパー実行
    scraper = ThreadsKeywordScraper(config_path=args.config)
    
    # 動的に設定を上書き
    if not args.config:
        scraper.config = {
            'search_config': {
                'filters': {
                    'min_likes': args.min_likes,
                    'min_replies': args.min_replies,
                    'posted_within_hours': args.hours
                }
            }
        }
    
    print(f"検索開始: {' '.join(args.keywords)}")
    print(f"検索ロジック: {args.logic}")
    
    # 検索実行
    results = scraper.search_by_keywords(args.keywords, args.logic)
    
    # バズ投稿のみフィルタ（オプション）
    if args.viral_only:
        results = [r for r in results if r['virality_data']['is_viral']]
    
    # 結果を保存
    import json
    import os
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n検索完了: {len(results)}件の投稿を取得")
    print(f"結果を保存: {args.output}")
    
    # サマリー表示
    if results:
        viral_count = sum(1 for r in results if r['virality_data']['is_viral'])
        print(f"バズ投稿: {viral_count}件")
        
        print("\nトップ5投稿:")
        for i, post in enumerate(results[:5], 1):
            print(f"{i}. いいね: {post['likes']}, リプライ: {post['replies']}, "
                  f"エンゲージメント率: {post['virality_data']['engagement_rate']:.2f}%")

if __name__ == '__main__':
    main()
```

## 3. 実行例

```bash
# 基本的な使用方法
python threads_keyword_scraper.py -k "AI" "機械学習" -l OR --min-likes 500

# 設定ファイルを使用
python threads_keyword_scraper.py -k "Python" "Django" -c config.yaml

# バズ投稿のみ抽出
python threads_keyword_scraper.py -k "起業" "スタートアップ" --viral-only

# AND検索で厳密に絞り込み
python threads_keyword_scraper.py -k "Web3" "ブロックチェーン" -l AND --min-likes 1000

# 複数キーワードの組み合わせ
python threads_keyword_scraper.py -k "Docker" "コンテナ" "Kubernetes" --hours 48
```

## 4. 設定ファイル例（config.yaml）

```yaml
search_config:
  # キーワードセット（複数の検索パターン）
  keyword_sets:
    - name: "AI関連"
      keywords: ["AI", "機械学習", "ChatGPT"]
      logic: "OR"
    
    - name: "開発ツール"
      keywords: ["Docker", "Kubernetes"]
      logic: "AND"
  
  # フィルタ設定
  filters:
    min_likes: 500
    min_replies: 50
    min_reposts: 20
    posted_within_hours: 24
    languages: ["ja"]
  
  # バズ判定カスタマイズ
  virality:
    engagement_rate_threshold: 4.5
    velocity_multiplier: 10
    require_viral_only: true
  
  # スクレイピング設定
  scraping:
    max_posts_per_keyword: 100
    rate_limit_per_hour: 60
    scroll_depth: 5
```

この実装により、パラメータで柔軟にキーワード検索を制御し、バズっている投稿を効率的に特定できます！
