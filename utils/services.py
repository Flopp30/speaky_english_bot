import datetime
import json
import uuid

from django.conf import settings
from yookassa import Payment as Yoo_Payment, Configuration

from payment.models import Payment
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
# {
# 	'amount':
# 	{
# 		'currency': 'RUB',
# 		'value': '100.00'
# 	},
# 	'confirmation':
# 	{
# 		'confirmation_url':
# 		'https://yoomoney.ru/checkout/payments/v2/contract?orderId=2c9218c3-000f-5000-8000-1d2da753c135',
# 		'return_url': 'https://google.com/',
# 		'type': 'redirect'
# 	},
# 	'created_at': '2023-09-12T06:28:19.595Z',
# 	'description': "Оформление подписки по тарифу 'WOW на срок 12 дней",
# 	'id': '2c9218c3-000f-5000-8000-1d2da753c135',
# 	'metadata':
# 	{},
# 	'paid': False,
# 	'payment_method':
# 	{
# 		'id': '2c9218c3-000f-5000-8000-1d2da753c135',
# 		'saved': False,
# 		'type': 'bank_card'
# 	},
# 	'recipient':
# 	{
# 		'account_id': '210134',
# 		'gateway_id': '2069098'
# 	},
# 	'refundable': False,
# 	'status': 'pending',
# 	'test': True
# }


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


def renew_sub():
    now = datetime.datetime.now()
    expired_subs = Subscription.objects.filter(unsub_date__lte=now, is_active=True).select_related('product', 'user')
    for sub in expired_subs:
        metadata = {
            "sub_id": sub.id,
            "user_id": sub.user.id,
            "chat_id": sub.user.chat_id,
            "renew": True,
        }
        yoo_payment = get_auto_payment(sub=sub, product=sub.product, metadata=metadata)
        Payment.objects.create(
            status=yoo_payment.get('status'),
            payment_service_id=yoo_payment.get('id'),
            amount=yoo_payment.get('amount').get('value'),
            currency=yoo_payment.get('amount').get('currency'),
            user=sub.user
        )
