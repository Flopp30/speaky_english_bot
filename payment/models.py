from django.db import models

from user.models import User
from utils.models import NOT_NULLABLE, NULLABLE


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
    payment_service_id = models.UUIDField(
        verbose_name='Id платежа в платежной системе',
        **NOT_NULLABLE,
        unique=False
    )
    payment_service = models.CharField(
        verbose_name='Платежная система',
        **NOT_NULLABLE,
        max_length=128,
        default='YooKassa'
    )
    amount = models.FloatField(verbose_name='Сумма платежа', **NOT_NULLABLE)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='payments',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return f"{self.id}: {self.amount} from {self.user}"

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
