from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ig', '0006_instagrambusinessaccount_long_lived_user_token_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='IGPostInsight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('impressions', models.IntegerField(blank=True, null=True, verbose_name='インプレッション')),
                ('reach', models.IntegerField(blank=True, null=True, verbose_name='リーチ')),
                ('likes', models.IntegerField(blank=True, null=True, verbose_name='いいね')),
                ('comments', models.IntegerField(blank=True, null=True, verbose_name='コメント')),
                ('shares', models.IntegerField(blank=True, null=True, verbose_name='シェア')),
                ('saved', models.IntegerField(blank=True, null=True, verbose_name='保存')),
                ('recorded_at', models.DateTimeField(auto_now_add=True, verbose_name='記録日時')),
                ('post', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='insights',
                    to='ig.igpost',
                )),
            ],
            options={
                'verbose_name': 'Instagram投稿インサイト',
                'verbose_name_plural': 'Instagram投稿インサイト',
                'db_table': 'meta_ig_post_insights',
                'ordering': ['-recorded_at'],
                'indexes': [
                    models.Index(fields=['post', '-recorded_at'], name='meta_ig_pos_post_id_idx'),
                ],
            },
        ),
    ]
