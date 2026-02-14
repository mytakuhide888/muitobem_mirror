# -*- coding: utf-8 -*-
# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0013_thbuzzauthor_profile_pic_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='fortune_relevance_score',
            field=models.FloatField(
                blank=True,
                help_text='ジャンル適合度 + マネタイズ度の加重スコア (0-100)',
                null=True,
                verbose_name='占い適合スコア',
            ),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='genre_tags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='自動検出: ["占い","タロット","スピリチュアル"...]',
                verbose_name='ジャンルタグ',
            ),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='monetization_signals',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='検出: ["STORES","LINE","有料鑑定"...]',
                verbose_name='マネタイズシグナル',
            ),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='auto_excluded_reason',
            field=models.CharField(
                blank=True,
                default='',
                max_length=200,
                verbose_name='自動対象外理由',
            ),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(
                fields=['-fortune_relevance_score'],
                name='bza_fortune_score_desc',
            ),
        ),
    ]
