from django.db import models

from datetime import datetime

from product.models import Product
from user.models import User
from utils.models import NULLABLE, NOT_NULLABLE


class SubPeriodTypes(models.TextChoices):
    DAYS = 'day'
    MONTHS = 'month'
    YEARS = 'year'


class Subscription(models.Model):
    is_auto_renew = models.BooleanField(
        verbose_name='Автоматически продлевать?', default=False)
    sub_start_date = models.DateTimeField(
        verbose_name='Дата начала подписки', **NULLABLE)
    unsub_date = models.DateTimeField(
        verbose_name='Дата окончания подписки', **NULLABLE)

    verified_payment_id = models.UUIDField(
        verbose_name='Подтвержденный ID платежа (автоматическое продление подписки)',
        **NULLABLE,
    )
    product = models.ForeignKey(
        Product,
        verbose_name='Продукт',
        related_name='subscriptions',
        on_delete=models.DO_NOTHING,
        **NOT_NULLABLE
    )
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='subscriptions',
        on_delete=models.DO_NOTHING,
        **NOT_NULLABLE
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна?'
    )

    # @property
    # def is_active(self):
    #     now = datetime.now()
    #     return self.sub_start_date <= now <= self.unsub_date

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
