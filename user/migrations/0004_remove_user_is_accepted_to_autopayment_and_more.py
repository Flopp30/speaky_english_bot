# Generated by Django 4.2.4 on 2023-09-07 07:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_user_last_visit_time_user_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_accepted_to_autopayment',
        ),
        migrations.RemoveField(
            model_name='user',
            name='verified_payment_id',
        ),
    ]