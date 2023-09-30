import logging

import requests
from django.conf import settings

from user.models import User

logger = logging.getLogger(__name__)


def get_tg_payload(chat_id, message_text, buttons: [{str: str}] = None):
    payload = {
        'chat_id': chat_id,
        'text': message_text,
        'parse_mode': 'HTML',
    }
    if buttons:
        keyboard_buttons = []
        for button in buttons:
            for text, url in button.items():
                keyboard_buttons.append({
                    "text": text,
                    "url": url
                })
        payload['reply_markup'] = {'inline_keyboard': [keyboard_buttons]}
    return payload


def send_tg_message_to_admins_from_django(text: str):
    admins_chat_id = User.objects.filter(is_superuser=True).values_list('chat_id', flat=True)
    for chat_id in admins_chat_id:
        payload = get_tg_payload(chat_id=chat_id, message_text=text)
        response = requests.post(settings.TG_SEND_MESSAGE_URL, json=payload)
        if response.status_code != 200:
            logger.error(f'Не удалось отправить сообщение: {payload}\n{response.text}')


async def send_message_to_admins_from_bot(bot_context, text):
    admins_chat_id = User.objects.filter(is_superuser=True).values_list('chat_id', flat=True)
    async for chat_id in admins_chat_id:
        await bot_context.bot.send_message(
            chat_id=chat_id,
            text=text,
        )


async def check_bot_context(update, context):
    if not context.user_data.get('user'):
        context.user_data['user'], _ = await User.objects.prefetch_related('subscriptions').aget_or_create(
            chat_id=update.effective_chat.id,
            defaults={
                'username': update.effective_chat.username
            }
        )
    if not context.user_data.get('subscriptions'):
        context.user_data['subscriptions'] = {
            subscription.id: subscription
            async for subscription in
            context.user_data['user'].subscriptions.filter(
                is_active=True).select_related('product')
        }
