# -*- coding: utf-8 -*-
"""
NGワードチェッカー — 投稿文・プロフィール文の法令違反自動検出

対象法令:
  - 消費者契約法（霊感商法の禁止）
  - 薬機法（医薬品的効能の表示禁止）
  - 景品表示法（優良誤認・確実性の表現）
  - 特定商取引法
  - 占い相談対象外事項

参考: CLAUDE/strategy/fortune_business_strategy.md 第11章
"""
import re
from typing import Dict, List, Tuple

# ─── カテゴリ定義 ───
# 各カテゴリ: (カテゴリID, 表示名, 深刻度, 法令根拠, パターンリスト)
# パターン: (正規表現, NG理由, 修正案)

NG_CATEGORIES: List[Dict] = [
    {
        'id': 'reikan',
        'name': '霊感商法（消費者契約法違反）',
        'severity': 'critical',
        'law': '消費者契約法第4条第3項（霊感等による知見を用いた勧誘の取消し）',
        'patterns': [
            (r'受けないと.{0,6}(不幸|災い|災難|呪[いわ])', '不安を煽って購入を迫る表現', '削除してください'),
            (r'(呪[いわ]|祟り|怨念|悪霊).{0,10}(解[くけ]|払[いうえ]|除[くけ])', '霊感商法にあたる除霊・浄化の勧誘', '削除してください'),
            (r'(除霊|浄霊|お祓い|厄払い).{0,6}(しないと|しなければ|必要)', '恐怖を煽った有料サービスへの誘導', '削除してください'),
            (r'(前世|因縁|業|カルマ).{0,8}(清算|解消).{0,6}(しないと|しなければ)', '前世・因縁を理由にした勧誘', '削除してください'),
            (r'(このまま|放置|放っておく)と.{0,10}(大変|危険|取り返し)', '不安を煽る脅迫的表現', '前向きな表現に変更してください'),
            (r'(守護霊|背後霊|霊).{0,4}が.{0,6}(怒|泣|苦し)', '霊的存在で恐怖を煽る表現', '削除してください'),
        ],
    },
    {
        'id': 'certainty',
        'name': '確実性表現（景品表示法違反）',
        'severity': 'high',
        'law': '景品表示法第5条第1号（優良誤認表示）',
        'patterns': [
            (r'(必ず|絶対に?|確実に?|100%.?|百%).{0,6}(叶[いうえ]|成功|当た[るり]|的中)', '効果の確実性を保証する表現', '「〜かもしれません」「〜の可能性があります」に変更'),
            (r'(誰でも|誰もが|全員).{0,6}(効果|結果|成果|幸[せ運])', '全員への効果を保証する表現', '「多くの方に」「〜を目指して」に変更'),
            (r'(間違いな[いく]|疑いな[いく]).{0,4}(効果|結果|幸[せ運])', '確実性を暗示する表現', '「〜と感じる方が多い」に変更'),
            (r'(保証|約束).{0,4}(します|いたします|できます)', '結果の保証表現', '「〜をお手伝いします」に変更'),
            (r'(的中率|当選率|成功率).{0,2}(\d{2,3}|[89]\d).{0,1}%', '高い確率を示す数値表現', '具体的な数値を削除してください'),
        ],
    },
    {
        'id': 'yakki',
        'name': '薬機法違反（医薬品的効能の表示）',
        'severity': 'critical',
        'law': '医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律（薬機法）第68条',
        'patterns': [
            (r'(パワーストーン|ブレスレット|アクセサリー|石).{0,8}(治[るす]|治癒|治療|回復)', '雑貨に医薬品的効能を表示', '「お守りとして」「美しさを楽しむ」に変更'),
            (r'(身につける|着ける|持つ).{0,4}だけで.{0,6}(病|痛|症状|体調).{0,4}(治|良く|改善)', '装着だけで病気が治る表現', '削除してください'),
            (r'(病気|疾患|症状|持病).{0,6}(治[るす]|完治|改善|回復)', '病気の治癒を暗示する表現', '「心身のリラックスをサポート」に変更'),
            (r'(うつ|鬱|不眠|頭痛|腰痛|生理痛).{0,6}(治[るす]|解消|改善)', '具体的な症状の改善を約束', '削除してください'),
            (r'(がん|癌|ガン|糖尿病|高血圧).{0,6}(効[くき]|予防|治)', '重篤な疾患への効果を示唆', '絶対に削除してください'),
        ],
    },
    {
        'id': 'keihin',
        'name': '景品表示法違反（有利誤認・優良誤認）',
        'severity': 'high',
        'law': '景品表示法第5条（不当な表示の禁止）',
        'patterns': [
            (r'(今だけ|期間限定|本日限り).{0,6}(無料|半額|[0-9０-９]+%\s*[oO][fF][fF]|割引)', '常時行っている場合は有利誤認', '本当に期間限定の場合のみ使用してください'),
            (r'(業界|日本).{0,2}(一|No\.?1|ナンバーワン|トップ|最[高強大])', '根拠のない最上級表現', '客観的根拠がない場合は削除してください'),
            (r'(通常|定価).{0,4}[0-9０-９,，]+円.{0,4}(→|が|を).{0,4}[0-9０-９,，]+円', '二重価格表示（実態と異なる場合）', '実際の販売価格のみ記載してください'),
        ],
    },
    {
        'id': 'scope',
        'name': '相談対象外事項',
        'severity': 'warning',
        'law': '占い業界のガイドライン・自主規制',
        'patterns': [
            (r'(ギャンブル|競馬|競輪|パチンコ|宝くじ|ロト).{0,6}(当た[るり]|勝[てつ]|予想|的中)', 'ギャンブルの結果予測は対象外', '「ギャンブル関連のご相談はお受けしておりません」を明記'),
            (r'(生死|寿命|余命|死期).{0,6}(占|鑑定|視|分か[るり])', '人の生死に関する占いは対象外', '削除してください。生死の占いは行わない旨を明記'),
            (r'(試験|受験|合格|資格).{0,6}(必ず|絶対|確実|的中|当た)', '試験の合否保証は対象外', '「合格に向けたエネルギーの流れをお伝えします」に変更'),
            (r'(裁判|訴訟|法的|弁護士).{0,6}(結果|勝[てつ]|有利)', '法的問題の結果予測は対象外', '「法的な問題は専門家にご相談ください」を明記'),
        ],
    },
    {
        'id': 'ai_disclosure',
        'name': 'AI利用に関する誤認リスク',
        'severity': 'warning',
        'law': '景品表示法（優良誤認）・詐欺罪',
        'patterns': [
            (r'(私|わたし|僕|俺)が.{0,4}(一つ一つ|ひとつひとつ|全て|すべて).{0,4}(占|鑑定|視)', 'AI支援の場合、全て手作業と誤認させる表現', '「AIを活用しながら丁寧に鑑定」等に変更'),
        ],
    },
]


def check_ng_words(text: str) -> Dict:
    """
    テキスト内のNGワードをチェックし、検出結果を返す。

    Returns:
        {
            'has_issues': bool,
            'total_count': int,
            'critical_count': int,
            'high_count': int,
            'warning_count': int,
            'results': [
                {
                    'category_id': str,
                    'category_name': str,
                    'severity': str,
                    'law': str,
                    'matches': [
                        {
                            'matched_text': str,
                            'reason': str,
                            'suggestion': str,
                            'position': int,
                        }
                    ]
                }
            ]
        }
    """
    if not text or not text.strip():
        return {
            'has_issues': False,
            'total_count': 0,
            'critical_count': 0,
            'high_count': 0,
            'warning_count': 0,
            'results': [],
        }

    results = []
    total_count = 0
    severity_counts = {'critical': 0, 'high': 0, 'warning': 0}

    for cat in NG_CATEGORIES:
        matches = []
        seen_spans = set()

        for pattern_str, reason, suggestion in cat['patterns']:
            try:
                for m in re.finditer(pattern_str, text):
                    # 同一箇所の重複検出を防止
                    span = (m.start(), m.end())
                    if span in seen_spans:
                        continue
                    seen_spans.add(span)

                    matches.append({
                        'matched_text': m.group(),
                        'reason': reason,
                        'suggestion': suggestion,
                        'position': m.start(),
                    })
            except re.error:
                continue

        if matches:
            matches.sort(key=lambda x: x['position'])
            results.append({
                'category_id': cat['id'],
                'category_name': cat['name'],
                'severity': cat['severity'],
                'law': cat['law'],
                'matches': matches,
            })
            total_count += len(matches)
            severity_counts[cat['severity']] = severity_counts.get(cat['severity'], 0) + len(matches)

    return {
        'has_issues': total_count > 0,
        'total_count': total_count,
        'critical_count': severity_counts.get('critical', 0),
        'high_count': severity_counts.get('high', 0),
        'warning_count': severity_counts.get('warning', 0),
        'results': results,
    }
