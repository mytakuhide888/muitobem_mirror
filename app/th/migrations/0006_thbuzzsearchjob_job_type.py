from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0005_thbuzzauthor_is_favorited'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzsearchjob',
            name='job_type',
            field=models.CharField(
                choices=[('keyword', 'キーワード検索'), ('account', 'アカウント取得')],
                default='keyword',
                max_length=20,
                verbose_name='ジョブ種別',
            ),
        ),
    ]
