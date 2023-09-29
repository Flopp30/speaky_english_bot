import logging

import requests
from django.conf import settings

from user.models import User


logger = logging.getLogger(__name__)


def get_tg_payload(chat_id, message_text, buttons: [{str: str}] = None):
    payload = {'chat_id': chat_id,
               'text': message_text, }
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


def send_tg_message_to_admins(text: str):
    admins_chat_id = User.objects.filter(is_superuser=True).values_list('chat_id', flat=True)
    for chat_id in admins_chat_id:
        payload = get_tg_payload(chat_id=chat_id, message_text=text)
        response = requests.post(settings.TG_SEND_MESSAGE_URL, json=payload)
        if response.status_code != 200:
            logger.error(f'Не удалось отправить сообщение: {payload}\n{response.text}')
