# Generated by Django 4.2.4 on 2023-09-17 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscription', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='is_auto_renew',
            field=models.BooleanField(default=True, verbose_name='Автоматически продлевать?'),
        ),
    ]
