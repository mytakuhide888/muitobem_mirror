from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0009_thbuzzauthor_quality_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='thbuzzauthor',
            name='is_excluded',
            field=models.BooleanField(default=False, verbose_name='対象外'),
        ),
    ]
