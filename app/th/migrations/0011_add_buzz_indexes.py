from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0010_thbuzzauthor_is_excluded'),
    ]

    operations = [
        # ─── THBuzzAuthor ───
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['-updated_at'], name='bza_updated_at_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['is_excluded'], name='bza_is_excluded'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['is_favorited'], name='bza_is_favorited'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['-growth_score'], name='bza_growth_score_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['-quality_score'], name='bza_quality_score_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['followers_count'], name='bza_followers_count'),
        ),
        migrations.AddIndex(
            model_name='thbuzzauthor',
            index=models.Index(fields=['account_age_days'], name='bza_account_age_days'),
        ),
        # ─── THBuzzPost ───
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['-scraped_at'], name='bzp_scraped_at_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['author', '-scraped_at'], name='bzp_author_scraped'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['-posted_at'], name='bzp_posted_at_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['search_keyword'], name='bzp_search_keyword'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['is_viral'], name='bzp_is_viral'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['-like_count'], name='bzp_like_count_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['-engagement_score'], name='bzp_eng_score_desc'),
        ),
        migrations.AddIndex(
            model_name='thbuzzpost',
            index=models.Index(fields=['-engagement_rate'], name='bzp_eng_rate_desc'),
        ),
    ]
