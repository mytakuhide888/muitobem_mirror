from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0004_thbuzzpost_media_type_thbuzzpost_media_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_favorited',
            field=models.BooleanField(default=False, verbose_name='お気に入り'),
        ),
    ]
