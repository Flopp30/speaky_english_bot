from django.db import models

from user.models import User
from utils.models import NOT_NULLABLE


class PaymentStatus(models.TextChoices):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    CANCELED = 'canceled'


class Payment(models.Model):
    id = models.BigIntegerField(verbose_name='Id', primary_key=True)
    status = models.CharField(
        verbose_name='Статус платежа',
        max_length=128,
        choices=PaymentStatus.choices,
        **NOT_NULLABLE
    )
    amount = models.FloatField(verbose_name='Сумма платежа', **NOT_NULLABLE)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = models.ForeignKey(
        User,
        verbose_name='Платежи',
        related_name='payments',
        on_delete=models.DO_NOTHING
    )
