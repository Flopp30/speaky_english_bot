import logging
import re

import requests

from datetime import timedelta, datetime
from textwrap import dedent

from asgiref.sync import sync_to_async
from django.template import Template, Context

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (ApplicationBuilder, ContextTypes,
                          CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler,
                          filters)

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from user.models import User

logger = logging.getLogger('tbot')


class Command(BaseCommand):
    def handle(self, *args, **options):
        main()


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_token, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.token = tg_token

    def emit(self, record):
        log_entry = self.format(record)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': log_entry,
        }
        requests.post(url=url, data=data)


def get_date(date: datetime):
    month_list = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    return f"{date.day} {month_list[date.month - 1]}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open('bot_parts/messages/greeting.html') as file:
        template = Template(file.read())
    chat_id = update.effective_chat.id
    user = await User.objects.filter(chat_id=chat_id).afirst()
    if user:
        username = user.username
    else:
        username = None
        await User.objects.acreate(
            username=update.effective_user.username,
            chat_id=chat_id,
            id=update.effective_user.id
        )

    context.user_data['user'] = user
    keyboard = []
    await context.bot.send_message(
        chat_id,
        text=template.render(Context({'username': username})),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'START'


async def user_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.message:
        user_reply = update.message.text
    elif update.callback_query.data:
        user_reply = update.callback_query.data
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = context.user_data.get('state', 'START')
    states_function = {
        'START': start
    }

    state_handler = states_function[user_state]
    next_state = await state_handler(update, context)
    context.user_data['state'] = next_state


def main():
    # telegram_handler = TelegramLogsHandler(settings.ADMIN_TG_BOT, settings.ADMIN_TG_CHAT)
    # telegram_handler.setLevel(logging.WARNING)
    # logger.addHandler(telegram_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(settings.LOG_LEVEL)
    # stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    pattern = re.compile(r'subscribe!.*')
    application.add_handler(CallbackQueryHandler(user_input_handler))
    application.add_handler(MessageHandler(filters.TEXT, user_input_handler))
    application.add_handler(CommandHandler('start', user_input_handler))
    try:
        if settings.BOT_MODE == 'webhook':
            logger.warning('Bot started in WEBHOOK mode')
            application.run_webhook(
                listen="0.0.0.0",
                port=5000,
                url_path=settings.TELEGRAM_TOKEN,
                webhook_url=f"{settings.WEBHOOK_URL}{settings.TELEGRAM_TOKEN}"
            )
        else:
            logger.warning('Bot started in POLLING mode')
            application.run_polling()
    except Exception:
        import traceback
        logger.warning(traceback.format_exc())
