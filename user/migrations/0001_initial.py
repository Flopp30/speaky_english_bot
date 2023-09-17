# Generated by Django 4.2.4 on 2023-09-17 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='ФИО')),
                ('role', models.CharField(blank=True, max_length=128, null=True, verbose_name='Роль')),
                ('description', models.TextField(blank=True, default='', null=True, verbose_name='Описание')),
                ('photo', models.ImageField(upload_to='teacher_photos/', verbose_name='Фотография преподавателя')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен?')),
            ],
            options={
                'verbose_name': 'Преподаватель',
                'verbose_name_plural': 'Преподаватели',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.BigIntegerField(verbose_name='Chat ID')),
                ('username', models.CharField(blank=True, max_length=100, null=True, verbose_name='Ник пользователя')),
                ('state', models.CharField(default='NEW', max_length=50, verbose_name='Статус переписки в боте')),
                ('last_visit_time', models.DateTimeField(auto_now=True, verbose_name='Время последнего посещения')),
                ('registration_datetime', models.DateTimeField(auto_now_add=True, verbose_name='Дата и время регистрации')),
                ('first_sub_date', models.DateTimeField(blank=True, null=True, verbose_name='Дата первой подписки')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен?')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='Администратор')),
            ],
            options={
                'verbose_name': 'Пользователь',
                'verbose_name_plural': 'Пользователи',
            },
        ),
    ]
