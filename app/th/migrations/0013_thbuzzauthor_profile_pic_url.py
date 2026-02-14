from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0012_thbuzzsearchjob_error_traceback'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='profile_pic_url',
            field=models.URLField(blank=True, default='', max_length=500, verbose_name='プロフィール画像URL'),
        ),
    ]
