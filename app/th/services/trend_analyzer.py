# -*- coding: utf-8 -*-
"""
Googleトレンド連携サービス
pytrends を使ってキーワードの検索ボリューム推移・関連クエリを取得する。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Googleトレンドデータ取得クラス"""

    def __init__(self, hl='ja-JP', tz=540):
        self.hl = hl
        self.tz = tz

    def _build_pytrends(self):
        from pytrends.request import TrendReq
        return TrendReq(hl=self.hl, tz=self.tz)

    def get_keyword_interest(
        self,
        keywords: list[str],
        timeframe: str = 'today 3-m',
        geo: str = 'JP',
    ) -> Optional[dict]:
        """
        キーワードの検索ボリューム推移を取得する。

        Returns:
            {
                'dates': ['2026-01-01', ...],
                'series': {
                    'keyword1': [10, 20, ...],
                    'keyword2': [5, 15, ...],
                },
                'timeframe': 'today 3-m',
            }
        """
        try:
            pt = self._build_pytrends()
            pt.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
            df = pt.interest_over_time()

            if df.empty:
                return {'dates': [], 'series': {}, 'timeframe': timeframe}

            # isPartial カラムを除去
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])

            dates = [d.strftime('%Y-%m-%d') for d in df.index]
            series = {}
            for col in df.columns:
                series[col] = df[col].tolist()

            return {
                'dates': dates,
                'series': series,
                'timeframe': timeframe,
            }
        except Exception as e:
            logger.exception("get_keyword_interest エラー: keywords=%s", keywords)
            return None

    def get_related_queries(
        self,
        keyword: str,
        geo: str = 'JP',
    ) -> Optional[dict]:
        """
        関連キーワードを取得する。

        Returns:
            {
                'top': [{'query': '...', 'value': 100}, ...],
                'rising': [{'query': '...', 'value': 200}, ...],
            }
        """
        try:
            pt = self._build_pytrends()
            pt.build_payload([keyword], geo=geo)
            related = pt.related_queries()

            result = {'top': [], 'rising': []}

            if keyword in related:
                kw_data = related[keyword]
                if kw_data.get('top') is not None and not kw_data['top'].empty:
                    result['top'] = kw_data['top'].to_dict('records')[:20]
                if kw_data.get('rising') is not None and not kw_data['rising'].empty:
                    result['rising'] = kw_data['rising'].to_dict('records')[:20]

            return result
        except Exception as e:
            logger.exception("get_related_queries エラー: keyword=%s", keyword)
            return None

    def get_related_topics(
        self,
        keyword: str,
        geo: str = 'JP',
    ) -> Optional[dict]:
        """
        関連トピックを取得する。

        Returns:
            {
                'top': [{'topic_title': '...', 'value': 100}, ...],
                'rising': [{'topic_title': '...', 'value': 200}, ...],
            }
        """
        try:
            pt = self._build_pytrends()
            pt.build_payload([keyword], geo=geo)
            topics = pt.related_topics()

            result = {'top': [], 'rising': []}

            if keyword in topics:
                kw_data = topics[keyword]
                if kw_data.get('top') is not None and not kw_data['top'].empty:
                    top_df = kw_data['top'][['topic_title', 'value']].head(20)
                    result['top'] = top_df.to_dict('records')
                if kw_data.get('rising') is not None and not kw_data['rising'].empty:
                    rising_df = kw_data['rising'][['topic_title', 'value']].head(20)
                    result['rising'] = rising_df.to_dict('records')

            return result
        except Exception as e:
            logger.exception("get_related_topics エラー: keyword=%s", keyword)
            return None
