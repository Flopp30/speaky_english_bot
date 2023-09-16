import datetime
import json

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from yookassa.domain.exceptions import BadRequestError

from payment.models import Payment, PaymentStatus, Refund, RefundStatus
from product.models import LinkSources, ExternalLink
from speakybot import settings
from subscription.models import Subscription
from utils.helpers import get_tg_payload
from utils.services import create_yoo_refund

TG_SEND_MESSAGE_URL = settings.TELEGRAM_API_URL + 'sendMessage'


class YooPaymentCallBackView(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        response_data = json.loads(request.body.decode("utf-8"))
        print(response_data)
        response_obj, event = response_data.get('object'), response_data.get('event')
        metadata = response_obj.get('metadata')
        if event in ("payment.succeeded", "payment.canceled"):
            user_id, chat_id, is_renew = metadata.get('user_id'), metadata.get('chat_id'), metadata.get('renew') == 'true'
            try:
                payment = Payment.objects.get(
                    payment_service='YooKassa',
                    payment_service_id=response_obj.get('id')
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
                payload = self._first_sub(event, payment, response_obj, user_id, product_id, english_lvl, chat_id)

            response = requests.post(TG_SEND_MESSAGE_URL, json=payload)
            if response.status_code != 200:
                # TODO обработать неотправленное уведомление пользователю с ссылкой на оплату
                pass

            payment.save()
        else:  # refund.succeeded
            refund = Refund.objects.get(payment_service_id=response_obj.get('id'))
            refund.status = RefundStatus.SUCCEEDED
            refund.payment.save()
            refund.save()
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
                try:
                    link = ExternalLink.objects.get(source=english_lvl).link
                    payload = get_tg_payload(chat_id=chat_id, message_text=text, buttons=[
                        {
                            'Чат клуба': link
                        }
                    ])
                except ExternalLink.DoesNotExist:
                    payload = get_tg_payload(chat_id=chat_id, message_text=text)
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


class RefundCreateView(View):
    model = Refund
    return_url = '/admin/payment/payment/'
    error_message = 'Что-то пошло не так. Попробуйте перезагрузить страницу и повторите попытку'
    refund_already_exist_message = 'Возврат уже был создан ранее. Обратитесь в YooKassa за уточнением'
    success_message = 'Возврат успешно создан'

    def post(self, request, **kwargs):
        payment_id = request.POST.get('payment_id')
        try:
            if payment_id and request.user.is_superuser:
                db_payment = Payment.objects.get(pk=payment_id)
            else:
                raise Payment.DoesNotExist
        except Payment.DoesNotExist:
            messages.add_message(request, messages.ERROR, self.error_message)
            return redirect(self.return_url)

        try:
            yoo_refund = create_yoo_refund(payment=db_payment)
        except BadRequestError:
            db_payment.is_refunded = True
            db_payment.save()
            messages.add_message(request, messages.WARNING, self.refund_already_exist_message)
            return redirect(self.return_url)

        Refund.objects.create(
            payment=db_payment,
            payment_service_id=yoo_refund.get('id')
        )
        db_payment.is_refunded = True
        db_payment.save()
        messages.add_message(request, messages.SUCCESS, self.success_message)
        return redirect(self.return_url)
