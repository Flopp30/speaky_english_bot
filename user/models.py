from datetime import timezone
from django.db import models

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
    registration_datetime = models.DateTimeField(
        verbose_name='Дата и время регистрации',
        auto_now_add=True,
    )


    def __str__(self) -> str:
        return f"Пользователь {self.username if self.username else 'Noname'}"

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
