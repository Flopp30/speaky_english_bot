import json
import uuid

from django.conf import settings
from yookassa import Payment as Yoo_Payment, Configuration


# Configuration.account_id = settings.YOO_SHOP_ID
# Configuration.secret_key = settings.YOO_TOKEN
Configuration.account_id = '210134'
Configuration.secret_key = 'test_MC3lMB_QVPrNgwbvtTAYXMnBvPzc0Nez5-mzvCCchIk'


def get_yoo_payment(**kwargs):
    idempotence_key = str(uuid.uuid4())
    payment = Yoo_Payment.create({
        "save_payment_method": True,
        "amount": {
            "value": kwargs.get("payment_amount"),
            "currency": kwargs.get("payment_currency"),
        },
        # "metadata": {
        # },
        "payment_method_data": {
            "type": "bank_card"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": 'https://google.com/',
        },
        "capture": True,
        "description": "Оформление подписки "
                       f"по тарифу '{kwargs.get('sub_humanize_name')}' на срок {kwargs.get('sub_period')}",
    }, idempotence_key)

    return json.loads(payment.json())


payment = get_yoo_payment(payment_amount=100, payment_currency='RUB', sub_humanize_name='WOW', sub_period='12 дней')
url = payment.get("confirmation", dict()).get("confirmation_url", None)
print(url)

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
