import datetime
import json

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from yookassa.domain.exceptions import BadRequestError

from payment.models import Payment, PaymentStatus, Refund, RefundStatus
from product.models import LinkSources, ExternalLink, ProductType, Product
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
        request_data = json.loads(request.body.decode("utf-8"))
        returned_obj, event = request_data.get('object'), request_data.get('event')
        match event:
            case "refund.succeeded":
                self.process_refund(returned_obj)

            case "payment.succeeded" | "payment.canceled":
                try:
                    payment = (
                        Payment.objects
                        .select_related('user', 'subscription')
                        .get(
                            payment_service='YooKassa',
                            payment_service_id=returned_obj.get('id')
                        )
                    )
                except (Payment.DoesNotExist):
                    # TODO обработать ошибку платежа?
                    return JsonResponse({"status": "success"})

                if event == "payment.succeeded":
                    self.process_payment_success(
                        payment=payment,
                        returned_obj=returned_obj,
                    )
                else:
                    self.process_payment_canceled(payment)

        return JsonResponse({"status": "success"})

    def process_payment_success(self, payment, returned_obj):
        payment.status = PaymentStatus.SUCCEEDED
        metadata = returned_obj.get('metadata')
        product = Product.objects.get(pk=metadata.get('product_id'))
        subscription, is_create = Subscription.objects.get_or_create(is_active=True, user=payment.user, product=product)

        if is_create:
            subscription.sub_start_date = datetime.datetime.now()
            subscription.unsub_date = datetime.datetime.now() + relativedelta(months=1)
            subscription.verified_payment_id = returned_obj.get('payment_method', {}).get('id', None)
            payment.subscription = subscription
        else:
            subscription.unsub_date = subscription.unsub_date + relativedelta(months=1)

        match product.id_name:
            case ProductType.SPEAKY_CLUB:
                unsub_date_formatted = subscription.unsub_date.strftime("%d-%m-%Y")
                english_lvl = metadata.get('english_lvl')
                group_name = LinkSources.SPEAK_CLUB_UPPER if english_lvl == 'upper' else LinkSources.SPEAK_CLUB_ADV
                link = ExternalLink.objects.filter(source=group_name).first().link

                if is_create and link:
                    text = ("Платеж совершен успешно.\n"
                            f"Подписка в '{group_name}' оформлена до {unsub_date_formatted}")
                    payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text, buttons=[
                        {
                            'Чат клуба': link
                        }
                    ])
                else:
                    text = (f"Платеж совершен успешно.\n"
                            f"Подписка в '{group_name}' продлена до {unsub_date_formatted}")
                    payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text)

            case ProductType.PERSONAL_LESSONS:
                # TODO Успешный ответ при оплате персональных уроков
                pass
            case ProductType.GROUP_LESSONS:
                # TODO Успешный ответ при оплате групп
                pass

        subscription.save()
        payment.save()
        self.send_tg_message(payload)

    def process_payment_canceled(self, payment):
        payment.status = PaymentStatus.CANCELED
        text = "Платеж перешел в статус отменен. Пожалуйста, повторите попытку оплаты."
        payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text)
        payment.save()
        self.send_tg_message(payload)

    def process_refund(self, returned_obj):
        refund_id = returned_obj.get('id')
        payment_service_id = returned_obj.get('payment_id')
        refund = (
            Refund.objects
            .select_related('payment', 'payment__subscription', 'payment__subscription__product', 'payment__user')
            .get(payment_service_id=refund_id, payment__payment_service_id=payment_service_id)
        )
        subscription = refund.payment.subscription
        text = f"Возврат суммы {refund.payment.amount} {refund.payment.currency} проведен успешно.\n"

        is_subscription_remain = refund.success()

        if is_subscription_remain:
            text += (f"Подписка на '{subscription.product.name}' закончится:\n ."
                     f"{subscription.unsub_date.strftime('%d-%m-%Y')}")
        else:
            text += f"Подписка на '{subscription.product.name}' завершена.\n ."

        payload = get_tg_payload(chat_id=refund.payment.user.chat_id, message_text=text)
        self.send_tg_message(payload)
        # TODO отправить Даше сообщение о успешно проведенном возврате?

    @staticmethod
    def send_tg_message(payload):
        response = requests.post(TG_SEND_MESSAGE_URL, json=payload)
        if response.status_code != 200:
            # TODO обработать неотправленное уведомление пользователю с ссылкой на оплату
            pass


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
        messages.add_message(request, messages.SUCCESS, self.success_message)
        return redirect(self.return_url)
