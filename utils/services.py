import json
import uuid

from django.conf import settings
from yookassa import Payment as Yoo_Payment, Configuration

from product.models import Product
from subscription.models import Subscription

Configuration.account_id = settings.YOO_SHOP_ID
Configuration.secret_key = settings.YOO_TOKEN


def get_yoo_payment(payment_amount, payment_currency, product_name, sub_period, metadata: dict = {}):
    idempotence_key = str(uuid.uuid4())
    payment = Yoo_Payment.create({
        "save_payment_method": True,
        "amount": {
            "value": payment_amount,
            "currency": payment_currency,
        },
        "metadata": metadata | {"renew": False},
        "payment_method_data": {
            "type": "bank_card"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": settings.TG_BOT_URL,
        },
        "capture": True,
        "description": "Оформление подписки "
                       f"по тарифу '{product_name}' на срок {sub_period}",
    }, idempotence_key)

    return json.loads(payment.json())


def get_auto_payment(sub: Subscription, product: Product, metadata: dict = {}):
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
