# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0015_merge_20260214_2317'),
    ]

    operations = [
        # THBuzzAuthor に新フィールド追加
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_attention_needed',
            field=models.BooleanField(default=False, help_text='自動巡回で成長スコア閾値超え + 占い適合のアカウント', verbose_name='要注目'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='attention_set_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='要注目フラグ設定日時'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_analyzed',
            field=models.BooleanField(default=False, help_text='構造化分析メモが記入済み', verbose_name='分析済み'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['is_attention_needed'], name='bza_attention_needed'),
        ),
        # THBuzzAuthorAnalysis 新規モデル
        migrations.CreateModel(
            name='THBuzzAuthorAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('factor_profile', models.TextField(blank=True, default='', verbose_name='プロフィール/表示名の工夫')),
                ('factor_concept', models.TextField(blank=True, default='', verbose_name='コンセプト（何者か、ギャップ）')),
                ('factor_content', models.TextField(blank=True, default='', verbose_name='投稿内容の傾向')),
                ('factor_format', models.TextField(blank=True, default='', verbose_name='投稿形式の使い分け')),
                ('factor_frequency', models.TextField(blank=True, default='', verbose_name='投稿頻度・タイミング')),
                ('factor_engagement', models.TextField(blank=True, default='', verbose_name='エンゲージメントの取り方')),
                ('factor_funnel', models.TextField(blank=True, default='', verbose_name='導線設計（bio→LINE→鑑定等）')),
                ('factor_other', models.TextField(blank=True, default='', verbose_name='その他の要因')),
                ('overall_assessment', models.TextField(blank=True, default='', verbose_name='総合評価')),
                ('concept_inspiration', models.TextField(blank=True, default='', verbose_name='この垢から得たコンセプトのヒント')),
                ('differentiation_idea', models.TextField(blank=True, default='', verbose_name='ずらしのアイデア')),
                ('analyzed_at', models.DateTimeField(auto_now=True, verbose_name='分析日時')),
                ('author', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analysis',
                    to='th.thbuzzauthor',
                    verbose_name='投稿者',
                )),
            ],
            options={
                'verbose_name': '投稿者分析メモ',
                'verbose_name_plural': '投稿者分析メモ',
                'db_table': 'meta_th_buzz_author_analysis',
            },
        ),
    ]
