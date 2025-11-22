from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('social', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dmmessage',
            old_name='sender_external_user_id',
            new_name='user_id',
        ),
        migrations.RenameField(
            model_name='dmmessage',
            old_name='received_at',
            new_name='sent_at',
        ),
        migrations.AlterField(
            model_name='dmmessage',
            name='user_id',
            field=models.CharField(max_length=100, verbose_name='ユーザーID'),
        ),
        migrations.AlterField(
            model_name='dmmessage',
            name='sent_at',
            field=models.DateTimeField(verbose_name='送受信時間'),
        ),
        migrations.AddField(
            model_name='dmmessage',
            name='direction',
            field=models.CharField(
                choices=[('IN', 'In'), ('OUT', 'Out')],
                default='IN',
                max_length=3,
                verbose_name='方向',
            ),
        ),
        migrations.AddField(
            model_name='dmmessage',
            name='external_ids',
            field=models.JSONField(blank=True, default=dict, verbose_name='外部ID'),
        ),
        migrations.RenameField(
            model_name='webhookevent',
            old_name='event_type',
            new_name='field',
        ),
        migrations.AlterField(
            model_name='webhookevent',
            name='field',
            field=models.CharField(blank=True, max_length=100, verbose_name='フィールド'),
        ),
        migrations.RemoveField(
            model_name='webhookevent',
            name='processed',
        ),
        migrations.AddField(
            model_name='webhookevent',
            name='content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='webhookevent',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='webhookevent',
            name='signature_valid',
            field=models.BooleanField(default=True, verbose_name='署名検証'),
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'job_type',
                    models.CharField(
                        choices=[('REPLY', 'Reply'), ('PUBLISH', 'Publish'), ('INSIGHT', 'Insight')],
                        max_length=20,
                        verbose_name='ジョブ種別',
                    ),
                ),
                (
                    'platform',
                    models.CharField(
                        choices=[('THREADS', 'Threads'), ('INSTAGRAM', 'Instagram')],
                        max_length=20,
                        verbose_name='プラットフォーム',
                    ),
                ),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('args', models.JSONField(blank=True, default=dict, verbose_name='引数')),
                ('run_at', models.DateTimeField(verbose_name='実行予定時刻')),
                (
                    'status',
                    models.CharField(
                        choices=[('PENDING', 'Pending'), ('RUNNING', 'Running'), ('DONE', 'Done'), ('FAILED', 'Failed')],
                        default='PENDING',
                        max_length=20,
                        verbose_name='ステータス',
                    ),
                ),
                ('retries', models.IntegerField(default=0, verbose_name='リトライ回数')),
                ('last_error', models.TextField(blank=True, null=True, verbose_name='最終エラー')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                (
                    'content_type',
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype'),
                ),
            ],
        ),
    ]
