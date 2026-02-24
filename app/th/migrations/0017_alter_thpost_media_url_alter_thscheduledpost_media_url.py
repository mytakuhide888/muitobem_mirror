from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('th', '0016_auto_pipeline_and_analysis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='thpost',
            name='media_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='メディアURL'),
        ),
        migrations.AlterField(
            model_name='thscheduledpost',
            name='media_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='メディアURL'),
        ),
    ]
