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
    id = models.BigIntegerField(verbose_name='ID', primary_key=True)
    is_auto_renew = models.BooleanField(
        verbose_name='Автоматически продлевать?', default=False)
    sub_start_date = models.DateTimeField(
        verbose_name='Дата начала подписки', **NULLABLE)
    unsub_date = models.DateTimeField(
        verbose_name='Дата окончания подписки', **NULLABLE)
    sub_period = models.IntegerField(
        verbose_name='Длительность подписки.', **NOT_NULLABLE, default=1)

    sub_period_type = models.CharField(
        verbose_name='Тип периода подписки (день, месяц. год)',
        max_length=128,
        choices=SubPeriodTypes.choices,
        default=SubPeriodTypes.MONTHS,
        **NOT_NULLABLE
    )

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

    @property
    def is_active(self):
        now = datetime.now()
        return now >= self.sub_start_date and now <= self.unsub_date

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
