import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View

from product.models import Product
from user.models import User
from utils.helpers import get_tg_payload
from utils.services import create_db_payment


class SendMessageView(View):
    return_url = '/admin/user/user/'
    error_message = 'Что-то пошло не так. Попробуйте перезагрузить страницу и повторите попытку'
    success_message = 'Сообщение успешно отправлено'

    async def post(self, request, **kwargs):
        user = await User.objects.aget(pk=request.POST.get('user_id'))
        text = request.POST.get('message_text')
        if request.POST.get('with_link') == 'True':
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
            messages.add_message(request, messages.SUCCESS, self.success_message)
        else:
            messages.add_message(request, messages.ERROR, self.error_message)
        return redirect(self.return_url)

