from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0006_thbuzzsearchjob_job_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_concept_candidate',
            field=models.BooleanField(default=False, verbose_name='コンセプト候補'),
        ),
    ]
