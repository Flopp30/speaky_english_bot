import datetime
import json
import logging

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from yookassa.domain.exceptions import BadRequestError

from payment.models import Payment, PaymentStatus, Refund
from product.models import LinkSources, ExternalLink, ProductType, Product
from speakybot import settings
from subscription.models import Subscription
from user.models import User
from utils.helpers import get_tg_payload, send_tg_message_to_admins_from_django
from utils.services import create_yoo_refund

logger = logging.getLogger(__name__)


class YooPaymentCallBackView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        request_data = json.loads(request.body.decode("utf-8"))
        returned_obj, event = request_data.get('object'), request_data.get('event')
        match event:
            case "refund.succeeded":
                try:
                    self.process_refund(returned_obj)
                except Refund.DoesNotExist:
                    logger.error(f'Problem with refund: {request_data}')
                    return JsonResponse({"status": "success"})

            case "payment.succeeded" | "payment.canceled":
                try:
                    payment = (
                        Payment.objects
                        .select_related('user', 'subscription')
                        .get(
                            payment_service='YooKassa',
                            payment_service_id=returned_obj.get('id'),
                            status=PaymentStatus.PENDING,
                        )
                    )
                except Payment.DoesNotExist:
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
            subscription.user.first_sub_date = datetime.datetime.now()
            subscription.user.save()
            payment.subscription.save()
        else:
            subscription.unsub_date = subscription.unsub_date + relativedelta(months=1)

        unsub_date_formatted = subscription.unsub_date.strftime("%d-%m-%Y")
        text = "Платеж совершен успешно.\n"
        match product.id_name:
            case ProductType.SPEAKY_CLUB:
                english_lvl = metadata.get('english_lvl')
                if english_lvl == 'upper_wed':
                    link_source = LinkSources.CHAT_SPEAK_CLUB_UPPER_WED
                    group_name = 'Разговорный клуб High Inter / Upper (Среда 19:00)'
                else:
                    link_source = LinkSources.CHAT_SPEAK_CLUB_UPPER_THUR
                    group_name = 'Разговорный клуб High Inter / Upper (Четверг 19:00)'

                link = ExternalLink.objects.filter(source=link_source).first()

                if is_create and link:
                    text += f"Подписка в '{group_name}' оформлена до {unsub_date_formatted}"
                    payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text, buttons=[
                        {
                            'Чат клуба': link.link
                        }
                    ])
                else:
                    text += f"Подписка в '{group_name}' продлена до {unsub_date_formatted}"
                    payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text)

            case _:
                if product.id_name == ProductType.PERSONAL_LESSONS:
                    group_name = 'групповые занятия'
                else:
                    group_name = 'индивидуальные занятия'
                if is_create:
                    text += f"Подписка на {group_name} оформлена до {unsub_date_formatted}"
                else:
                    text += f"Подписка на {group_name} продлена до {unsub_date_formatted}"
                payload = get_tg_payload(chat_id=payment.user.chat_id, message_text=text)
        subscription.save()
        payment.save()
        self.send_tg_message(payload)

        admins_text = (f"Поступил платеж {payment.amount} {payment.currency} от @{subscription.user.username}")
        send_tg_message_to_admins_from_django(admins_text)

    def process_payment_canceled(self, payment):
        payment.status = PaymentStatus.CANCELED
        if payment.subscription:
            if payment.subscription.unsub_date - relativedelta(months=1) < timezone.now():
                payment.subscription.is_active = False
                payment.subscription.is_auto_renew = False
            else:
                payment.subscription.unsub_date -= relativedelta(months=1)
            payment.subscription.save()
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
            text += (f"Подписка на '{subscription.product.name}' закончится:\n"
                     f"{subscription.unsub_date.strftime('%d-%m-%Y')}")
        else:
            text += f"Подписка на '{subscription.product.name}' завершена."

        payload = get_tg_payload(chat_id=refund.payment.user.chat_id, message_text=text)
        self.send_tg_message(payload)

        admins_text = (f"Возврат суммы {refund.payment.amount} {refund.payment.currency} для пользователя "
                       f"@{refund.payment.user.username} проведен успешно.\n")
        send_tg_message_to_admins_from_django(admins_text)

    @staticmethod
    def send_tg_message(payload):
        response = requests.post(settings.TG_SEND_MESSAGE_URL, json=payload)
        if response.status_code != 200:
            logger.error(f'Не удалось отправить сообщение: {payload}')


class RefundCreateView(View):
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
