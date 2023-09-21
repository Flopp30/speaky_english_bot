import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View

from product.models import Product, ProductType
from subscription.models import Subscription
from user.models import User
from utils.helpers import get_tg_payload
from utils.services import create_db_payment


class SendMessageView(View):
    return_url = '/admin/user/user/'
    error_message = '{success_counter} сообщений отправлено успешно. {error_counter} - не отправлены'
    success_message = '{success_counter} сообщений отправлены успешно'

    async def post(self, request, **kwargs):
        to_users = request.POST.get('to_users')
        user_pk = request.POST.get('user_id')
        error_counter, success_counter = 0, 0
        users = self.get_users(to_users, user_pk)
        text = request.POST.get('message_text')
        with_link = request.POST.get('with_link') == 'True'
        async for user in users:
            if with_link:
                product = await Product.objects.aget(pk=request.POST.get('product_id'))
                url = await create_db_payment(product, user)
                payload = get_tg_payload(chat_id=user.chat_id, message_text=text, buttons=[
                    {
                        f'Оплатить {product.price} {product.currency}': url
                    }
                ])
            else:
                payload = get_tg_payload(chat_id=user.chat_id, message_text=text)
            response = requests.post(settings.TG_SEND_MESSAGE_URL, json=payload)
            if response.status_code == 200:
                success_counter += 1
            else:
                error_counter += 1
        if error_counter:
            mes_text = self.error_message.format(error_counter=error_counter, success_counter=success_counter)
            messages.add_message(request, messages.INFO, mes_text)
        else:
            mex_text = self.success_message.format(success_counter=success_counter)
            messages.add_message(request, messages.SUCCESS, mex_text)
        return redirect(self.return_url)

    @staticmethod
    def get_users(field_value, pk=None):
        match field_value:
            case 'current':
                return User.objects.filter(pk=pk)
            case 'all_unsub':
                user_ids = (
                    Subscription.objects
                    .select_related('product')
                    .filter(is_active=True)
                    .values_list('user_id', flat=True)
                    .distinct()
                )
                return User.objects.exclude(pk__in=user_ids)
            case 'all_subs':
                user_ids = (
                    Subscription.objects
                    .select_related('product')
                    .filter(is_active=True)
                    .values_list('user_id', flat=True)
                    .distinct()
                )
                return User.objects.filter(pk__in=user_ids)
            case 'personal':
                user_ids = (
                    Subscription.objects
                    .select_related('product')
                    .filter(is_active=True, product__id_name=ProductType.PERSONAL_LESSONS)
                    .values_list('user_id', flat=True)
                    .distinct()
                )
                return User.objects.filter(pk__in=user_ids)
            case 'group':
                user_ids = (
                    Subscription.objects
                    .select_related('product')
                    .filter(is_active=True, product__id_name=ProductType.GROUP_LESSONS)
                    .values_list('user_id', flat=True)
                    .distinct()
                )
                return User.objects.filter(pk__in=user_ids)
            case 'speak_club':
                user_ids = (
                    Subscription.objects
                    .select_related('product')
                    .filter(is_active=True, product__id_name=ProductType.SPEAKY_CLUB)
                    .values_list('user_id', flat=True)
                    .distinct()
                )
                return User.objects.filter(pk__in=user_ids)
            case 'all':
                return User.objects.all()
            case _:
                return []
