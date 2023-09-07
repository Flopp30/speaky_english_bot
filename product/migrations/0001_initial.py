# Generated by Django 4.2.4 on 2023-09-07 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, verbose_name='id')),
                ('price_rub', models.FloatField(verbose_name='Цена в рублях')),
                ('price_usd', models.FloatField(blank=True, null=True, verbose_name='Цена в долларах')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Описание продукта')),
            ],
        ),
    ]
