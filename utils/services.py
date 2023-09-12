import json
import uuid

from django.conf import settings
from yookassa import Payment as Yoo_Payment, Configuration

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
        "metadata": metadata,
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


# payment = get_yoo_payment(payment_amount=100, payment_currency='RUB', product_name='WOW', sub_period='12 дней')
# print(payment)
# url = payment.get("confirmation", dict()).get("confirmation_url", None)
# print(url)

# def get_auto_payment(sub: Subscription, user: User):
#     idempotence_key = str(uuid.uuid4())
#     payment = Yoo_Payment.create(
#         {
#             "amount": {
#                 "value": sub.payment_amount,
#                 "currency": sub.payment_currency,
#             },
#             "capture": True,
#             "payment_method_id": user.verified_payment_id,
#             "description": f"Продление подписки по тарифу '{sub.humanize_name}' на срок {sub.payment_name}",
#         }, idempotence_key
#     )
#     return json.loads(payment.json())
