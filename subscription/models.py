from django.db import models

from datetime import datetime

from product.models import Product
from user.models import User
from utils.models import NULLABLE, NOT_NULLABLE


class Subscription(models.Model):
    is_auto_renew = models.BooleanField(
        verbose_name='Автоматически продлевать?', default=True)
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

    def __str__(self):
        return f'Подписка на {self.product.name} до {self.unsub_date.strftime("%d-%m-%Y")}'

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    @classmethod
    def fields_to_report(cls):
        return (
            'id',
            'is_active',
            'sub_start_date',
            'unsub_date',
            'product',
            'user',
            'is_auto_renew',
        )
