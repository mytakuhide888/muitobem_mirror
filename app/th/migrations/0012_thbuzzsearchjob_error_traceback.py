from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0011_add_buzz_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzsearchjob',
            name='error_traceback',
            field=models.TextField(blank=True, default='', verbose_name='エラートレースバック'),
        ),
    ]
