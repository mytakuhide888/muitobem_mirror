from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0008_merge_20260213_1111'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='quality_score',
            field=models.FloatField(blank=True, null=True, verbose_name='品質スコア'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_quality_account',
            field=models.BooleanField(default=False, verbose_name='優良アカウント'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='good_post_ratio',
            field=models.FloatField(blank=True, null=True, verbose_name='良い投稿の割合'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='recent_post_count',
            field=models.IntegerField(blank=True, null=True, verbose_name='直近30日の投稿数'),
        ),
        migrations.AddField(
            model_name='thbuzzauthor',
            name='avg_post_interval_days',
            field=models.FloatField(blank=True, null=True, verbose_name='平均投稿間隔(日)'),
        ),
    ]
