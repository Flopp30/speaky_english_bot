import logging
import re

import requests

from asyncio import sleep

from datetime import timedelta, datetime
from textwrap import dedent

from asgiref.sync import sync_to_async
from django.template import Context, Template as DjTemplate

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, ContextTypes,
                          CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, PrefixHandler,
                          filters)

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone
from yookassa import Configuration

from payment.models import Payment
from product.models import Product, ProductType, ExternalLink, LinkSources
from templates.models import Template
from subscription.models import Subscription
from user.models import User, Teacher
from utils.models import MessageTemplates, MessageTeachers
from utils.services import create_db_payment
from utils.periodic_tasks import renew_sub_hourly

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
    context.user_data['user'], _ = await User.objects.prefetch_related('subscriptions').aget_or_create(
        chat_id=chat_id,
        defaults={
            'username': update.effective_chat.username
        }
    )
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
    context.user_data['subscriptions'] = {subscription.id: subscription async for subscription in
                                          context.user_data['user'].subscriptions.filter(
                                              is_active=True).select_related('product')}
    keyboard = [
        [InlineKeyboardButton("Разговорный клуб", callback_data='speak_club')],
        [InlineKeyboardButton("Групповые занятия",
                              callback_data='group_lessons')],
        [InlineKeyboardButton("Индивидуальные занятия",
                              callback_data='personal_lessons')],
    ]
    if context.user_data['subscriptions']:
        keyboard.append([InlineKeyboardButton(
            'Ваши активные подписки', callback_data='current_subscriptions')])
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
    choices = {
        'speak_club': speak_club_start,
        'group_lessons': group_club_start,
        'personal_lessons': personal_lessons_start,
        'current_subscriptions': show_current_subscriptions,
    }
    if (callback := choices.get(update.callback_query.data)):
        return await callback(update, context)
    return 'WELCOME_CHOICE'


async def show_current_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton(
            f'{subscription.product.name}', callback_data=subscription.id)]
        for subscription in context.user_data['subscriptions'].values()
    ]
    keyboard.append([InlineKeyboardButton('Назад', callback_data='back')])
    subs_text = '\n'.join([f"{subscription.product.name} до {subscription.unsub_date.strftime('%Y-%m-%d')}\
                           {'автопродление включено' if subscription.is_auto_renew else ''}"
                           for subscription in context.user_data['subscriptions'].values()])
    text = dedent(f"""В настоящее время вы подписаны на следующие продукты:
                  {subs_text}
                  Хотите отредактировать свои текущие подписки?""")
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'USER_SUBSCRIPTIONS_CHOICE'


async def handle_user_subscriptions_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'USER_SUBSCRIPTIONS_CHOICE'
    if update.callback_query.data == 'back':
        return await welcome_letter(update, context)
    chat_id = update.effective_chat.id
    try:
        sub_id = int(update.callback_query.data)
    except ValueError:
        return 'USER_SUBSCRIPTIONS_CHOICE'
    subscription = context.user_data['subscriptions'].get(sub_id)
    if not subscription:
        return 'USER_SUBSCRIPTIONS_CHOICE'
    text = dedent(f"""Подписка на {subscription.product.name}
    Стоимость {subscription.product.price} {subscription.product.currency}
    Активна до {subscription.unsub_date.strftime('%Y-%m-%d')}
    Автопродление {'включено' if subscription.is_auto_renew else 'отключено'}
""")
    keyboard = [
        [InlineKeyboardButton('Отключить автопродление',
                              callback_data=f'turn_off-{subscription.id}')]
        if subscription.is_auto_renew else
        [InlineKeyboardButton('Включить автопродление',
                              callback_data=f'turn_on-{subscription.id}')],
        [InlineKeyboardButton('Назад', callback_data='back')]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'AWAIT_SUBSCRIPTION_ACTION'


async def handle_subscription_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'AWAIT_SUBSCRIPTION_ACTION'
    if update.callback_query.data == 'back':
        return await show_current_subscriptions(update, context)
    chat_id = update.effective_chat.id
    try:
        action, sub_id = update.callback_query.data.split('-')
    except ValueError:
        return 'AWAIT_SUBSCRIPTION_ACTION'
    subscription: Subscription = context.user_data['subscriptions'].get(
        int(sub_id))
    if not subscription:
        return 'AWAIT_SUBSCRIPTION_ACTION'
    if action == 'turn_on':
        if subscription.verified_payment_id:
            subscription.is_auto_renew = True
            await subscription.asave()
            text = f'Автопродление подписки на {subscription.product.name} включено'
        # TODO Обработать случай, когда нет сохраненного айдишника для постоянного платежа
    elif action == 'turn_off':
        subscription.is_auto_renew = False
        await subscription.asave()
        text = f'Автопродление подписки на {subscription.product.name} отключено'
    else:
        return 'AWAIT_SUBSCRIPTION_ACTION'
    await context.bot.send_message(
        chat_id=chat_id,
        text=text
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'START'


async def speak_club_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text_1 = MessageTemplates.get('speaky_club_1')
    text_2 = MessageTemplates.get('speaky_club_2')
    text_3 = MessageTemplates.get('speaky_club_3')
    text_4 = MessageTemplates.get('speaky_club_4')
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
    if ProductType.SPEAKY_CLUB in [
        subscription.product.id_name for subscription in
        context.user_data['subscriptions'].values()
    ]:
        text_4 = MessageTemplates.get('speaky_club_5')
        await context.bot.send_message(
            chat_id,
            text=text_4,
            parse_mode='HTML',
        )
        return 'START'
    await context.bot.send_message(
        chat_id,
        text=text_4,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )
    return 'SPEAK_CLUB_LEVEL_CHOICE'


async def handle_speak_club_level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not update.callback_query:
        return 'SPEAK_CLUB_LEVEL_CHOICE'
    if update.callback_query.data in ('upper', 'advanced'):
        user = context.user_data['user'] or await User.objects.aget(chat_id=chat_id)
        product = await Product.objects.aget(id_name="speaky_club")
        url = await create_db_payment(product, user, additional_data={"english_lvl": update.callback_query.data})
        keyboard = [
            [InlineKeyboardButton(
                f'Оплатить {product.price} {product.currency}', web_app=WebAppInfo(url=url))],
        ]
        await context.bot.send_message(
            chat_id,
            text="Ссылка на оплату месячной подписки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return "START"
    elif update.callback_query.data == 'lower':
        return await speak_club_lower(update, context)
    else:
        return await level_test(update, context)


async def speak_club_lower(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = MessageTemplates.get('speaky_club_choice_1')
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
    text = MessageTemplates.get('speaky_club_choice_2')
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
    text = MessageTemplates.get('level_choice_1')
    keyboard = [
        [InlineKeyboardButton('Да', callback_data='yes')],
        [InlineKeyboardButton('Нет', callback_data='no')]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'AWAIT_LEVEL_TEST_CONFIRMATION'


async def handle_level_test_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return 'AWAIT_LEVEL_TEST_CONFIRMATION'
    chat_id = update.effective_chat.id
    if update.callback_query.data == 'no':
        text = MessageTemplates.get('level_test_confirmation_no')
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
    elif update.callback_query.data == 'yes':
        text = MessageTemplates.get('level_test_confirmation_yes')
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
        )
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=update.effective_message.message_id
        )
        username = update.effective_chat.username
        async for user in User.objects.filter(is_superuser=True):
            await context.bot.send_message(
                chat_id=user.chat_id,
                text=F'Пользователь {username} хотел бы пройти тест своего языкового уровня'
            )
        return 'START'


async def group_club_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text_1 = MessageTemplates.get('group_lessons_1')
    text_2 = MessageTemplates.get('group_lessons_2')
    text_3 = MessageTemplates.get('group_lessons_3')
    link = await ExternalLink.objects.aget(source=LinkSources.GROUP_LESSONS)
    keyboard = [
        [InlineKeyboardButton('Анкета', url=link.link)]
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
    if 'group_lessons' in [subscription.product.id_name for subscription in
                           context.user_data['subscriptions'].values()]:
        text_4 = MessageTemplates.get('group_lessons_4')
        await context.bot.send_message(
            chat_id,
            text=text_4,
            parse_mode='HTML',
        )
        return 'START'
    await context.bot.send_message(
        chat_id=chat_id,
        text=text_3,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'START'


async def personal_lessons_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = MessageTemplates.get('personal_lessons_1')
    link = await ExternalLink.objects.aget(source=LinkSources.PRIVATE_LESSONS)
    keyboard = [
        [InlineKeyboardButton('Анкета', url=link.link)]
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
    if 'personal_lessons' in [subscription.product.id_name for subscription in
                              context.user_data['subscriptions'].values()]:
        text_4 = MessageTemplates.get('personal_lessons_2')
        await context.bot.send_message(
            chat_id,
            text=text_4,
            parse_mode='HTML',
        )
        return 'TEACHER_PAGINATION'
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


async def handle_admin_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not update.callback_query:
        return 'AWAIT_ADMIN_CHOICE'
    if update.callback_query.data == 'users':
        subscriptions = Subscription.objects.filter(
            is_active=True).select_related('product', 'user')
        groups = {}
        async for subscription in subscriptions:
            groups[subscription.product.name] = groups.get(
                subscription.product.name, []) + [subscription.user.username]
        groups_texts = '\n'.join(
            [f'<b>{key}</b>: {", ".join(value)}' for key, value in groups.items()])
        text = dedent(f"""
        В настоящее время активно {len(subscriptions)} подписок.
        Следующие группы:
        {groups_texts}
        Хотите отправить сообщения учащимся в группу?
    """)
        keyboard = [
            [InlineKeyboardButton(f'{key}', callback_data=key)
             for key in groups.keys()]
        ] + [[InlineKeyboardButton('В главное меню', callback_data='start')]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=update.effective_message.message_id
        )
        return 'AWAIT_ADMIN_GROUP_CHOICE'
    return 'AWAIT_ADMIN_CHOICE'


async def handle_admin_group_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not update.callback_query:
        return 'AWAIT_ADMIN_GROUP_CHOICE'
    response = update.callback_query.data
    if response == 'start':
        return await start(update, context)
    context.chat_data['group_for_message'] = response
    keyboard = [
        [InlineKeyboardButton('Вернуться к выбору групп',
                              callback_data='back')]
    ]
    text = dedent(f"""
    Введите сообщение, которое бы вы хотели отправить учащимся группы {response}.
""")
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=update.effective_message.message_id
    )
    return 'AWAIT_MESSAGE_FOR_GROUP'


async def prepare_message_for_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.callback_query and update.callback_query.data == 'back':
        return await handle_admin_choice(update, context)
    if update.message and update.message.text:
        group_name = context.chat_data.get('group_for_message')
        context.chat_data['message_to_send'] = update.message
        keyboard = [
            [InlineKeyboardButton('Отправить', callback_data='confirm'),
             InlineKeyboardButton('Изменить', callback_data='edit')],
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=update.message.text,
            entities=update.message.entities,
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Хотите отправить такое сообщение учащимся группы {group_name}?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return 'AWAIT_GROUP_MESSAGE_CONFIRMATION'


async def send_message_for_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not update.callback_query:
        return 'AWAIT_GROUP_MESSAGE_CONFIRMATION'
    group_name = context.chat_data.get('group_for_message')
    if update.callback_query.data == 'edit':
        keyboard = [
            [InlineKeyboardButton(
                'Вернуться к выбору групп', callback_data='back')]
        ]
        text = dedent(f"""
        Введите сообщение, которое бы вы хотели отправить учащимся группы {group_name}.
    """)
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=update.effective_message.message_id
        )
        return 'AWAIT_MESSAGE_FOR_GROUP'
    if update.callback_query.data != 'confirm':
        return await 'AWAIT_GROUP_MESSAGE_CONFIRMATION'
    group_subscriptions = Subscription.objects.select_related(
        'product', 'user').filter(product__name=group_name)
    message_to_send = context.chat_data['message_to_send']
    for subscription in group_subscriptions:
        await context.bot.send_message(
            chat_id=subscription.user.chat_id,
            text=message_to_send.message.text,
            entities=message_to_send.entities,
        )
    await context.bot.send_message(
        chat_id=chat_id,
        text=f'Сообщение отправлено учащимся группы {group_name}'
    )
    return await start(update, context)


async def user_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.user_data.get('user'):
        context.user_data['user'], _ = await User.objects.prefetch_related('subscriptions').aget_or_create(
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
        'AWAIT_LEVEL_TEST_CONFIRMATION': handle_level_test_confirmation,
        'TEACHER_PAGINATION': teacher_pagination,
        'AWAIT_ADMIN_CHOICE': handle_admin_choice,
        'AWAIT_ADMIN_GROUP_CHOICE': handle_admin_group_choice,
        'AWAIT_MESSAGE_FOR_GROUP': prepare_message_for_group,
        'AWAIT_GROUP_MESSAGE_CONFIRMATION': send_message_for_group,
        'AWAIT_SUBSCRIPTION_ACTION': handle_subscription_action,
        'USER_SUBSCRIPTIONS_CHOICE': handle_user_subscriptions_choice
    }

    state_handler = states_function[user_state]
    next_state = await state_handler(update, context)
    context.user_data['user'].state = next_state
    await context.user_data['user'].asave()


async def reload_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command, key = update.message.text.split('|')
    except ValueError:
        return
    if key == settings.INTERNAL_MESSAGE_KEY:
        if command == '!reload_teachers':
            await MessageTeachers.load_teachers(context)
        elif command == '!reload_templates':
            await MessageTemplates.load_templates(context)


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
    job_queue = application.job_queue
    job_queue.run_repeating(
        renew_sub_hourly, interval=timedelta(hours=1), first=5)
    job_queue.run_repeating(MessageTemplates.load_templates,
                            interval=timedelta(minutes=10), first=1)
    job_queue.run_repeating(MessageTeachers.load_teachers,
                            interval=timedelta(minutes=10), first=1)

    application.add_handler(PrefixHandler(
        '!', ['reload_templates', 'reload_teachers'], reload_from_db))
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
