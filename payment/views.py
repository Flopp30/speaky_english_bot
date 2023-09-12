import datetime
import json

from dateutil.relativedelta import relativedelta
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from payment.models import Payment, PaymentStatus
from subscription.models import Subscription


class YooPaymentCallBackView(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode("utf-8"))
        event = data.get('event')
        yoo_payment = data.get('object')
        try:
            payment = Payment.objects.get(
                payment_service='YooKassa',
                payment_service_id=yoo_payment.get('id')
            )
        except Payment.DoesNotExist:
            # TODO обработать ошибку платежа?
            return JsonResponse({"status": "success"})
        match event:
            case "payment.succeeded":
                payment.status = PaymentStatus.SUCCEEDED
                metadata = yoo_payment.get('metadata')
                now = datetime.datetime.now()
                one_month_later = now + relativedelta(months=1)
                verified_payment_id = yoo_payment.get('payment_method', {}).get('id', None)
                Subscription.objects.create(
                    is_auto_renew=True,
                    sub_start_date=now,
                    unsub_date=one_month_later,
                    verified_payment_id=verified_payment_id,
                    user_id=metadata.get('user_id'),
                    product_id=metadata.get('product_id'),
                )

                match metadata.get('english_lvl'):
                    # TODO отправить ссылку в зависимости от уровня английского и в целом уведомить о поступлении оплаты
                    case "upper":
                        pass
                    case "advanced":
                        pass

            case "payment.canceled":
                payment.status = PaymentStatus.CANCELED
                # TODO обработать ошибки платежа?
        payment.save()
        return JsonResponse({"status": "success"})

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
