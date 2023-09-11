import logging
import re

import requests

from asyncio import sleep

from datetime import timedelta, datetime
from textwrap import dedent

from asgiref.sync import sync_to_async
from django.template import Context, Template as DjTemplate

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InputFile, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, ContextTypes,
                          CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler,
                          filters)

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from templates.models import Template
from user.models import User, Teacher
from utils.models import MessageTemplates, MessageTeachers

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
    chat_id = update.effective_chat.id
    if context.user_data['user'].is_superuser:
        return await staff_functions_select(update, context)
    if context.user_data['user'].state != 'NEW':
        return await welcome_letter(update, context)
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
    context.user_data['user'].state = 'START'
    return 'START'


async def staff_functions_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = dedent(f"""
        Здравствуйте, {context.user_data['user'].username}.
        Хотите посмотреть списки пользователей с активными подписками?
    """)
    keyboard = [
        [InlineKeyboardButton('Активные пользователи', callback_data='users')]
    ]
    await context.bot.send_message(
        chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'AWAIT_ADMIN_CHOICE'


async def welcome_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("Разговорный клуб", callback_data='speak_club')],
        [InlineKeyboardButton("Групповые занятия",
                              callback_data='group_lessons')],
        [InlineKeyboardButton("Индивидуальные занятия",
                              callback_data='personal_lessons')],
    ]
    text = MessageTemplates.templates.get('welcome_letter', 'Нужен шаблон welcome_letter. {username}').format(
        username=context.user_data['user'].username)
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
        text=text,
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
    keyboard = [
        [InlineKeyboardButton('Анкета', url='http://example.com')]
    ]
    pagination_keyboard = [
        [InlineKeyboardButton(text='<<', callback_data='TEACHER_PREV')],
        [InlineKeyboardButton(text='>>', callback_data='TEACHER_NEXT')]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
    )
    message = None
    if MessageTeachers.teachers:
        teacher_info = MessageTeachers.teachers[0]
        photo_path, caption = teacher_info.get(
            "photo_path"), teacher_info.get("caption")
        with open(photo_path, 'rb') as photo_file:
            message = await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(photo_file),
                caption=caption,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(pagination_keyboard)
            )
    if message:
        context.chat_data.update({"current_teacher_list_position": 0})
        context.chat_data.update({"message_id": message.id})
    await context.bot.send_message(
        chat_id=chat_id,
        text='По ссылке ты можешь заполнить анкету',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'TEACHER_PAGINATION'


async def teacher_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_id = context.chat_data.get('message_id')
    current_list_position = context.chat_data.get(
        'current_teacher_list_position', 0)
    pagination_keyboard = [
        [InlineKeyboardButton(text='<<', callback_data='TEACHER_PREV')],
        [InlineKeyboardButton(text='>>', callback_data='TEACHER_NEXT')]
    ]
    if not update.callback_query:
        return 'TEACHER_PAGINATION'
    if not message_id:
        return 'START'
    elif update.callback_query.data in ('TEACHER_PREV', 'TEACHER_NEXT'):
        new_position = current_list_position
        if update.callback_query.data == "TEACHER_PREV":
            new_position = (current_list_position -
                            1) % len(MessageTeachers.teachers)
        elif update.callback_query.data == 'TEACHER_NEXT':
            new_position = (current_list_position +
                            1) % len(MessageTeachers.teachers)

        if new_position != current_list_position:
            teacher_info = MessageTeachers.teachers[new_position]

            photo_path, caption = teacher_info.get(
                'photo_path'), teacher_info.get('caption')
            with open(photo_path, 'rb') as photo_file:
                new_photo = InputMediaPhoto(photo_file)
                await context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=new_photo
                )
                message = await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(pagination_keyboard)
                )
            context.chat_data.update(
                {'current_teacher_list_position': new_position})
            context.chat_data.update({'message_id': message.id})
        return 'TEACHER_PAGINATION'
    return 'START'


async def user_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.user_data.get('user'):
        context.user_data['user'], _ = await User.objects.aget_or_create(
            chat_id=chat_id,
            defaults={
                'username': update.effective_chat.username
            }
        )
    if update.message:
        user_reply = update.message.text
    elif update.callback_query.data:
        user_reply = update.callback_query.data
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = context.user_data['user'].state or 'START'
    states_function = {
        'NEW': start,
        'START': start,
        'WELCOME_CHOICE': handle_welcome_choice,
        'SPEAK_CLUB_LEVEL_CHOICE': handle_speak_club_level_choice,
        'LOWER_LEVEL_CHOICE': handle_lower_level_choice,
        'AWAIT_VOICE': handle_voice_test,
        'TEACHER_PAGINATION': teacher_pagination,
        'AWAIT_ADMIN_CHOICE': handle_admin_choice,
    }

    state_handler = states_function[user_state]
    next_state = await state_handler(update, context)
    context.user_data['user'].state = next_state
    await context.user_data['user'].asave()


def main():
    import tracemalloc
    tracemalloc.start()
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
    for template in Template.objects.all():
        MessageTemplates.templates[template.name] = (
            template.content
            .replace('<div>', '').replace('</div>', '')
            .replace('<br />', '').replace('&nbsp;', '')
            .replace('<p>', '').replace('</p>', '')
        )

    for teacher in Teacher.objects.filter(is_active=True):
        photo_path = teacher.photo.path
        description = (
            teacher.description
            .replace('<div>', '').replace('</div>', '')
            .replace('<br />', '').replace('&nbsp;', '')
            .replace('<p>', '').replace('</p>', '')
        )
        caption = (
            f"<b>{teacher.name}</b>\n<i>{teacher.role}</i>\n\n{description}")

        MessageTeachers.teachers.append(
            {
                "photo_path": photo_path,
                "caption": caption
            }
        )
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
