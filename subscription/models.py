from django.db import models

from product.models import Product
from utils.models import NULLABLE, NOT_NULLABLE


class SubPeriodTypes(models.TextChoices):
    DAYS = 'day'
    MONTHS = 'month'
    YEARS = 'year'


class Subscription(models.Model):
    is_auto_renew = models.BooleanField(verbose_name='Автоматически продлевать?', default=False)
    sub_start_date = models.DateTimeField(verbose_name='Дата начала подписки', **NULLABLE)
    unsub_date = models.DateTimeField(verbose_name='Дата окончания подписки', **NULLABLE)
    sub_period = models.IntegerField(verbose_name='Длительность подписки.', **NOT_NULLABLE, default=1)
    sub_period_type = models.CharField(
        verbose_name='Тип периода подписки (день, месяц. год)',
        max_length=128,
        choices=SubPeriodTypes.choices,
        default=SubPeriodTypes.MONTHS,
        **NOT_NULLABLE
    )
    product = models.ForeignKey(
        Product,
        verbose_name='Продукт',
        related_name='subscriptions',
        on_delete=models.DO_NOTHING,
        default=None,
        **NULLABLE,
    )
