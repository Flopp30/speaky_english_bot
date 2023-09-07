# Generated by Django 4.2.4 on 2023-09-07 06:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user', '0004_remove_user_is_accepted_to_autopayment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='Id')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('succeeded', 'Succeeded'), ('canceled', 'Canceled')], max_length=128, verbose_name='Статус платежа')),
                ('amount', models.FloatField(verbose_name='Сумма платежа')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='payments', to='user.user', verbose_name='Платежи')),
            ],
        ),
    ]
