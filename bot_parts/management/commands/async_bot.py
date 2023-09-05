import logging
import re

import requests

from asyncio import sleep

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open('bot_parts/messages/greeting.html') as file:
        template = Template(file.read())
    chat_id = update.effective_chat.id
    if context.user_data.get('user'):
        return await welcome_letter(update, context)
    user, _ = await User.objects.aget_or_create(
        chat_id=chat_id,
        defaults={
            'username': update.effective_chat.username
        }
    )
    context.user_data['user'] = user
    text = dedent(f"""
        Привет ✨
        Это бот студии английского <b>Speaky</b>
        Нажми /start , чтобы начать
    """)
    await context.bot.send_message(
        chat_id,
        text=text,
        parse_mode='HTML',
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'START'


async def welcome_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("Разговорный клуб", callback_data='speak_club')],
        [InlineKeyboardButton("Групповые занятия",
                              callback_data='group_lessons')],
        [InlineKeyboardButton("Индивидуальные занятия",
                              callback_data='personal_lessons')],
    ]
    text = dedent(f"""
        Привет, @{context.user_data['user'].username}

        Я Дарья, одна из 5% лучших учителей мира и основатель Speaky Studio. Мы с командой знаем, как тебе достичь твоей цели в английском и будем рады помочь 😉

        Просто выбери один из форматов ниже:

        🔸 <b>Разговорный клуб</b>, где ты прокачаешь свой разговорный английский, \
            избавишься от языкового барьера, болтая на самые горячие темы с @dasha.speaky
            от 3000руб/мес

        🔸 <b>Групповые занятия</b>, где ты сможешь набрать базу, разложить знания по полочкам, \
            активировать пассивные знания и начать говорить с преподавателями из нашей команды
            от 500руб/занятие

        🔸 <b>Индивидуальные занятия</b>, где ты сможешь максимально быстро закрыть любой запрос, \
            даже самый узкий, занимаясь по программе, подобранной под ваши интересы и нужды с преподавателем из нашей команды
            от 1500руб/занятие
    """)
    await context.bot.send_message(
        chat_id,
        text=text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'WELCOME_CHOICE'


async def handle_welcome_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'WELCOME_CHOICE'
    if update.callback_query.data == 'speak_club':
        return await speak_club_start(update, context)
    elif update.callback_query.data == 'group_lessons':
        return await group_club_start(update, context)
    else:
        return await personal_lessons_start(update, context)


async def speak_club_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text_1 = dedent("""
        ⭐ <b>Разговорный клуб</b> поможет:

        💡говорить без страха
        💡вывести знания из пассива в актив
        💡пополнить словарный запас живой лексикой
        💡звучать натуральнее и естественнее
        💡не растерять уровень, а нарастить

        <b>Формат и цена</b>
        основное общение в парах
        встречи в Zoom по 60 минут
        стоимость встречи 1000руб, оплата за месяц

        🎁 <b>Только в сентябре: 3000руб/месяц</b>
        *скидка 1000руб сохранится до конца года для всех, вступивших в сентябре и занимающихся каждый месяц
    """)
    text_2 = dedent("""
        <b>Как проходит:</b>

        заранее ты получаешь файл с темой встречи, ссылками на статью / видео

        Quizlet с полезной лексикой по теме для подготовки

        ко встрече ты уже знаешь, что говорить (посмотрел / почитал об этом) и как говорить (изучил лексику из Quizlet)

        на встрече ты много общаешься в паре с peers, учителем, получаешь обратную связь, прокачиваешь навыкs peaking по полной
    """)
    text_3 = dedent("""
        <b>Расписание:</b>

        🔘High Inter / Upper-Inter
        СР, 19:00 по мск

        🔘Advanced
        ЧТ, 19:00 по мск
    """)
    text_4 = "<b>Выбери свой уровень</b>"
    keyboard = [
        [InlineKeyboardButton('High Inter / Upper', callback_data='upper')],
        [InlineKeyboardButton('Advanced', callback_data='advanced')],
        [InlineKeyboardButton('Мой уровень ниже', callback_data='lower')],
        [InlineKeyboardButton('Не знаю свой уровень',
                              callback_data='dont_know')],
    ]
    await context.bot.send_message(
        chat_id,
        text=text_1,
        parse_mode='HTML',
    )
    await sleep(3)
    await context.bot.send_message(
        chat_id,
        text=text_2,
        parse_mode='HTML',
    )
    await sleep(3)
    await context.bot.send_message(
        chat_id,
        text=text_3,
        parse_mode='HTML',
    )
    await sleep(3)
    await context.bot.send_message(
        chat_id,
        text=text_4,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )
    return 'SPEAK_CLUB_LEVEL_CHOICE'


async def handle_speak_club_level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'SPEAK_CLUB_LEVEL_CHOICE'
    if update.callback_query.data == 'upper':
        return  # TODO Сделать оплату
    elif update.callback_query.data == 'advanced':
        return  # TODO Сделать оплату
    elif update.callback_query.data == 'lower':
        return await speak_club_lower(update, context)
    else:
        return await level_test(update, context)


async def speak_club_lower(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = dedent("""
        ✨ Мы получили уведомление о том, что ваш уровень ниже intermediate, \
        но вы тоже хотели бы участвовать в разговорных клубах и напишем вам, как только такая возможность появится

        А пока, хотели бы рассмотреть групповые занятия со стоимостью 500руб / занятие?
    """)
    keyboard = [
        [InlineKeyboardButton('Да', callback_data='yes')],
        [InlineKeyboardButton('Нет', callback_data='No')]
    ]
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
    return 'LOWER_LEVEL_CHOICE'


async def handle_lower_level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'LOWER_LEVEL_CHOICE'
    if update.callback_query.data == 'yes':
        return await group_club_start(update, context)
    chat_id = update.effective_chat.id
    text = dedent("""
        ✨ Спасибо, что обратились к нашему помощнику

        Мы свяжемся с вами, как только у нас появится актуальное для вас предложение 
        До скорого 😉
    """)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'START'


async def level_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = dedent("""
        Мы поможем определить твой уровень 😉

        Прямо здесь, в боте, пришли голосовое сообщение длиной 2-4 минуты с ответом на вопросы:

        🔸 Tell shortly about your last trip wherever you went to: who did you go with? \
                  where to? what did you do there? how did you like it? would you like to go there again?

        🔸 What do you tend to do when you have some free time? How long have you been doing that? 

        ❗Важно: не готовьтесь к ответом на вопросы. \
                  Чтобы подобрать группу, в которой вам и вашим peers буду комфортно, \
                  нам важно оценить именно вашу спонтанную речь
    """)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'AWAIT_VOICE'


async def handle_voice_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO Сделать обработку voice_test
    return


async def group_club_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text_1 = dedent("""
        ⭐ <b>Групповые занятия</b> помогут:

        💡набрать базу знаний
        💡разложить по полочкам то, что ты уже знаешь
        💡выучить достаточно, чтобы свободно выражать мысли
        💡преодолеть языковой барьер, общаясь с peers в группе

        <b>Формат и цена:</b>
        занятия в Zoom по 60мин 2 раза в неделю
        домашние задания
        стоимость занятия 500руб, оплата за месяц
        до 6 человек
    """)
    text_2 = dedent("""
        <b>Как проходят:</b>

        курс English File от Oxford как основа
        доп. материалы - YouTube виде и не только
        интерактивные задания
        вывод в речь всего нового
        много speaking в парах
        регулярные revisions
    """)
    text_3 = dedent("""
        <b>Расписание:</b>

        🔘 Pre-Intermediate

        🔘 Intermediate

        ❗Если у вас другой уровень, укажите его в анкете по ссылке ниже, мы свяжемся с вами и сообщим, она каком этапе набор в группу вашего уровня

        🤩 <b>РАЗГОВОРНЫЙ КЛУБ</b> 🤩
                            с @dasha.speaky

        🍁 <b>Примерные темы сентября:</b>
        Board games - needed vocabulary
        How fake news spread
        Are emojis making us dumber?
        How to buy happiness
    """)
    keyboard = [
        [InlineKeyboardButton('Анкета', url='http://example.com')]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text_1,
        parse_mode='HTML',
    )
    await sleep(3)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text_2,
        parse_mode='HTML',
    )
    await sleep(3)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text_3,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'START'


async def personal_lessons_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = dedent("""
        ⭐<b>Индивидуальные занятия</b> помогут:

        💡заниматься с максимальным прогрессом
        💡быстро закрыть узкий запрос: подготовиться к собеседованию / экзамену / переезду и тп
        💡заниматься по программе, подобранной для ваших личных нужд и интересов

        <b>Формат и цена:</b>
        занятия в Zoom 60мин с преподавателем из команды 
        ваш индивидуальный график
        объем домашних заданий и программа зависит отт ваших задач
        стоимость от 1500руб/занятие, оплата за месяц
    """)
    # TODO Продумать отображение анкет преподавателей
    keyboard = [
        [InlineKeyboardButton('Анкета', url='http://example.com')]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'START'


async def user_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        'START': start,
        'WELCOME_CHOICE': handle_welcome_choice,
        'SPEAK_CLUB_LEVEL_CHOICE': handle_speak_club_level_choice,
        'LOWER_LEVEL_CHOICE': handle_lower_level_choice,
        'AWAIT_VOICE': handle_voice_test,
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
