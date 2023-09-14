import datetime
import json

import requests
from dateutil.relativedelta import relativedelta
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from payment.models import Payment, PaymentStatus
from product.models import LinkSources, ExternalLink
from speakybot import settings
from subscription.models import Subscription
from utils.helpers import get_tg_payload

TG_SEND_MESSAGE_URL = settings.TELEGRAM_API_URL + 'sendMessage'


class YooPaymentCallBackView(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        response_data = json.loads(request.body.decode("utf-8"))
        yoo_payment, event = response_data.get('object'), response_data.get('event')
        metadata = yoo_payment.get('metadata')
        user_id, chat_id, is_renew = metadata.get('user_id'), metadata.get('chat_id'), metadata.get('renew') == 'true'
        try:
            payment = Payment.objects.get(
                payment_service='YooKassa',
                payment_service_id=yoo_payment.get('id')
            )
        except Payment.DoesNotExist:
            # TODO обработать ошибку платежа?
            return JsonResponse({"status": "success"})

        if is_renew:
            sub_id = metadata.get('sub_id')
            payload = self._renew(event, payment, sub_id, chat_id)
        else:
            product_id = metadata.get('product_id')
            english_lvl = metadata.get('english_lvl')
            payload = self._first_sub(event, payment, yoo_payment, user_id, product_id, english_lvl, chat_id)

        response = requests.post(TG_SEND_MESSAGE_URL, json=payload)
        if response.status_code != 200:
            # TODO обработать неотправленное уведомление пользователю с ссылкой на оплату
            pass

        payment.save()
        return JsonResponse({"status": "success"})

    @staticmethod
    def _first_sub(event, payment, yoo_payment, user_id, product_id, english_lvl, chat_id):
        payload = None
        match event:
            case "payment.succeeded":
                payment.status = PaymentStatus.SUCCEEDED
                now = datetime.datetime.now()
                one_month_later = now + relativedelta(months=1)
                verified_payment_id = yoo_payment.get('payment_method', {}).get('id', None)
                Subscription.objects.create(
                    is_auto_renew=True,
                    sub_start_date=now,
                    unsub_date=one_month_later,
                    verified_payment_id=verified_payment_id,
                    user_id=user_id,
                    product_id=product_id,
                )
                text_base = "Платеж совершен успешно. Подписка на месяц оформлена. \nГруппа: {group_name}"
                match english_lvl:
                    case "upper":
                        english_lvl = LinkSources.SPEAK_CLUB_UPPER
                        text = text_base.format(group_name="Разговорный клуб High Inter / Upper")
                    case _:
                        english_lvl = LinkSources.SPEAK_CLUB_ADV
                        text = text_base.format(group_name='Разговорный клуб Advanced')

                link = ExternalLink.objects.get(source=english_lvl).link
                payload = get_tg_payload(chat_id=chat_id, message_text=text, buttons=[
                    {
                        'Чат клуба': link
                    }
                ])
            case "payment.canceled":
                payment.status = PaymentStatus.CANCELED
                text = "Платеж перешел в статус отменен. Пожалуйста, повторите попытку оплаты."
                payload = get_tg_payload(chat_id=chat_id, message_text=text)

        return payload

    @staticmethod
    def _renew(event, payment: Payment, sub_id, chat_id):
        subscription = Subscription.objects.select_related('product').get(id=sub_id)
        match event:
            case "payment.succeeded":
                payment.status = PaymentStatus.SUCCEEDED
                one_month_later = datetime.datetime.now() + relativedelta(months=1)
                subscription.unsub_date = one_month_later
                text = (f"Подписка на '{subscription.product.name}' успешно продлена.\n"
                        f"Следующее списание: {one_month_later.strftime('%d.%m.%Y')}")
            case "payment.canceled" | _:
                payment.status = PaymentStatus.CANCELED
                subscription.is_active = False
                text = f"Недостаточно средств на счете для продления подписки '{subscription.product.name}'"

        payload = get_tg_payload(chat_id=chat_id, message_text=text)
        subscription.save()
        return payload

# {'type': 'notification', 'event': 'payment.succeeded',
#  'object': {'id': '2c922376-000f-5000-a000-1daaca238abd', 'status': 'succeeded',
#             'amount': {'value': '1000.00', 'currency': 'RUB'},
#             'income_amount': {'value': '965.00', 'currency': 'RUB'},
#             'description': "Оформление подписки по тарифу 'Разговорный клуб на срок 1 месяц",
#             'recipient': {'account_id': '210134', 'gateway_id': '2069098'},
#             'payment_method': {'type': 'bank_card', 'id': '2c922376-000f-5000-a000-1daaca238abd', 'saved': True,
#                                'title': 'Bank card *4444',
#                                'card': {'first6': '555555', 'last4': '4444', 'expiry_year': '2025',
#                                         'expiry_month': '12', 'card_type': 'MasterCard', 'issuer_country': 'US'}},
#             'captured_at': '2023-09-12T07:14:24.673Z', 'created_at': '2023-09-12T07:13:58.597Z', 'test': True,
#             'refunded_amount': {'value': '0.00', 'currency': 'RUB'}, 'paid': True, 'refundable': True,
#             'metadata': {}, 'authorization_details': {'rrn': '679958686207242', 'auth_code': '699373',
#                                                       'three_d_secure': {'applied': False,
#                                                                          'method_completed': False,
#                                                                          'challenge_completed': False}}}}
