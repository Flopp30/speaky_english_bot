from django.db import models

from utils.models import NULLABLE, NOT_NULLABLE


class User(models.Model):
    chat_id = models.BigIntegerField(
        verbose_name='Chat ID',
        null=False,
        blank=False
    )
    username = models.CharField(
        verbose_name='Ник пользователя',
        max_length=100,
        blank=True,
        null=True,
    )

    state = models.CharField(
        verbose_name='Статус переписки в боте',
        max_length=50,
        default='NEW'
    )

    last_visit_time = models.DateTimeField(
        verbose_name='Время последнего посещения',
        auto_now=True,
    )
    registration_datetime = models.DateTimeField(
        verbose_name='Дата и время регистрации',
        auto_now_add=True,
    )

    first_sub_date = models.DateTimeField(
        verbose_name='Дата первой подписки',
        **NULLABLE,
    )

    is_active = models.BooleanField(
        verbose_name='Активен?',
        **NOT_NULLABLE,
        default=True,
    )

    is_superuser = models.BooleanField(
        verbose_name='Администратор',
        **NOT_NULLABLE,
        default=False,
    )

    def __str__(self) -> str:
        return f"Пользователь {self.username if self.username else 'Noname'}"

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
