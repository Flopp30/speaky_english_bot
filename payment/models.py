import datetime

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone

from subscription.models import Subscription
from user.models import User, NOT_NULLABLE, NULLABLE


class PaymentStatus(models.TextChoices):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    CANCELED = 'canceled'


class Payment(models.Model):
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
    currency = models.CharField(verbose_name='Валюта платежа', max_length=128, **NOT_NULLABLE, default='RUB')
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='payments',
        on_delete=models.DO_NOTHING
    )

    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Подписка',
        related_name='subscription',
        on_delete=models.DO_NOTHING,
        **NULLABLE
    )

    is_refunded = models.BooleanField(verbose_name='Возвращен?', default=False)

    @classmethod
    def fields_to_report(cls):
        return (
            'id',
            'status',
            'payment_service',
            'amount',
            'currency',
            'created_at',
            'updated_at',
            'user',
            'subscription',
            'is_refunded',
        )

    def __str__(self):
        return f"{self.id}: {self.amount} from {self.user}"

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'


class RefundStatus(models.TextChoices):
    CREATED = 'created'
    SUCCEEDED = 'succeeded'


class Refund(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, verbose_name='Возврат', related_name='refund')
    status = models.CharField(
        choices=RefundStatus.choices,
        verbose_name='Статус',
        default=RefundStatus.CREATED,
        max_length=128
    )
    payment_service_id = models.UUIDField(
        verbose_name='Id возврата в платежной системе',
        **NOT_NULLABLE,
        unique=False
    )
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)

    def __str__(self):
        return f"Refund for payment {self.payment.id}"

    def success(self):
        self.status = RefundStatus.SUCCEEDED
        self.payment.is_refunded = True
        is_subscription_remain = False
        if self.payment.subscription:
            if self.payment.subscription.unsub_date - relativedelta(months=1) < timezone.now():
                self.payment.subscription.is_active = False
                self.payment.subscription.is_auto_renew = False
            else:
                self.payment.subscription.unsub_date -= relativedelta(months=1)
                is_subscription_remain = True
            self.payment.subscription.save()

        self.payment.save()
        self.save()
        return is_subscription_remain

    class Meta:
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
