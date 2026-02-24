from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ig', '0007_igpostinsight'),
    ]

    operations = [
        migrations.AlterField(
            model_name='igpost',
            name='media_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='メディアURL'),
        ),
        migrations.AlterField(
            model_name='igscheduledpost',
            name='media_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='メディアURL'),
        ),
    ]
