import json
import uuid

from django.conf import settings
from yookassa import (
    Payment as Yoo_Payment,
    Configuration,
    Refund as Yoo_Refund,
)

from payment.models import Payment
from product.models import Product
from subscription.models import Subscription
from user.models import User

Configuration.account_id = settings.YOO_SHOP_ID
Configuration.secret_key = settings.YOO_TOKEN


def create_yoo_payment(payment_amount, payment_currency, product_name, sub_period, metadata: dict = {}) -> dict:
    idempotence_key = str(uuid.uuid4())
    payment = Yoo_Payment.create({
        "save_payment_method": True,
        "amount": {
            "value": payment_amount,
            "currency": payment_currency,
        },
        "metadata": metadata,
        "payment_method_data": {
            "type": "bank_card"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": settings.TG_BOT_URL,
        },
        "capture": True,
        "description": f"Оформление подписки по тарифу '{product_name}' на срок {sub_period}",
    }, idempotence_key)

    return json.loads(payment.json())


async def create_db_payment(product: Product, user: User, additional_data: dict = {}):
    yoo_payment = create_yoo_payment(
        payment_amount=product.price,
        payment_currency=product.currency,
        product_name=product.name,
        sub_period='1 месяц',
        metadata={
            'product_id': product.id,
            "user_id": user.id,
        } | additional_data
    )
    await Payment.objects.acreate(
        status=yoo_payment.get('status'),
        payment_service_id=yoo_payment.get('id'),
        amount=yoo_payment.get('amount').get('value'),
        currency=yoo_payment.get('amount').get('currency'),
        user=user
    )
    return yoo_payment.get("confirmation", dict()).get("confirmation_url", None)


def create_yoo_auto_payment(sub: Subscription, product: Product, metadata: dict = {}) -> dict:
    idempotence_key = str(uuid.uuid4())
    payment = Yoo_Payment.create(
        {
            "amount": {
                "value": product.price,
                "currency": product.currency,
            },
            "metadata": metadata,
            "capture": True,
            "payment_method_id": sub.verified_payment_id,
            "description": f"Продление подписки по тарифу '{product.name}' на срок 1 месяц",
        }, idempotence_key
    )
    return json.loads(payment.json())


def create_yoo_refund(payment: Payment) -> dict:
    refund = Yoo_Refund.create({
        "amount": {
            "value": payment.amount,
            "currency": payment.currency,
        },
        "payment_id": payment.payment_service_id,
    })
    return json.loads(refund.json())
