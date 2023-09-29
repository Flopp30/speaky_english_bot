import logging
from asyncio import sleep
from datetime import timedelta
from textwrap import dedent

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PrefixHandler,
    filters
)

from product.models import Product, ProductType, ExternalLink, LinkSources, SalesAvailability
from subscription.models import Subscription
from user.models import User
from utils.helpers import send_tg_message_to_admins
from utils.models import MessageTemplates, MessageTeachers
from utils.periodic_tasks import renew_sub_hourly, send_reminders_hourly
from utils.services import create_db_payment

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
    text = MessageTemplates.templates.get('welcome_letter').format(
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
    subs_text = '\n'.join([f"{subscription.product.name} до {subscription.unsub_date.strftime('%Y-%m-%d')}"
                           f"{'- автопродление' if subscription.is_auto_renew else ''}"
                           for subscription in context.user_data['subscriptions'].values()])
    text = dedent(f"В настоящее время вы подписаны на следующие продукты:"
                  f"{subs_text}"
                  "\nХотите отредактировать свои текущие подписки?")
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
    subscription: Subscription = context.user_data['subscriptions'].get(int(sub_id))
    if not subscription:
        return 'AWAIT_SUBSCRIPTION_ACTION'
    if action == 'turn_on':
        if subscription.verified_payment_id:
            subscription.is_auto_renew = True
            await subscription.asave()
            text = f'Автопродление подписки на {subscription.product.name} включено'
        else:
            text = (
                f'Для автопродления подписки {subscription.product.name} нам нужно получить хотя бы один '
                f'платеж из бота.\n После завершения текущей подписки - оформите её заново'
            )
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
    sales_availability = await SalesAvailability.objects.aget(pk=1)
    keyboard = []
    is_not_available = False
    if sales_availability.wednesday_upper:
        keyboard.append([InlineKeyboardButton('High Inter / Upper СР, 19:00', callback_data='upper_wed')])
    else:
        text_4 += ('\nК сожалению, в группе High Inter / Upper СР, 19:00 нет мест.')
        is_not_available = True
    if sales_availability.thursday_upper:
        keyboard.append([InlineKeyboardButton('High Inter / Upper ЧТ, 19:00', callback_data='upper_thur')])
    else:
        text_4 += '\nК сожалению, в группе High Inter / Upper ЧТ, 19:00 нет мест.'
        is_not_available = True
    if is_not_available:
        text_4 += '\n\nНапиши @dasha_speaky для уточнения. Мы точно сможем найти решение 🌍'

    keyboard.extend([
        [InlineKeyboardButton('Мой уровень ниже', callback_data='lower')],
        [InlineKeyboardButton('Не знаю свой уровень',
                              callback_data='dont_know')],
    ])
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
    if update.callback_query.data in ('upper_wed', 'upper_thur'):
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
        return "START_AFTER_CLUB_PAYMENT"
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
        tg_link = f'https://web.telegram.org/#{chat_id}'
        admins_text = (f'Пользователь @{username} хотел бы пройти тест своего языкового уровня\n'
                       f'Ссылка на пользователя: {tg_link}')
        send_tg_message_to_admins(admins_text)
        return 'START'


async def group_club_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text_1 = MessageTemplates.get('group_lessons_1')
    text_2 = MessageTemplates.get('group_lessons_2')
    text_3 = MessageTemplates.get('group_lessons_3')
    link = await ExternalLink.objects.aget(source=LinkSources.FORM_GROUP_LESSONS)
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
    return 'START_AFTER_GROUP_LESSONS'


async def personal_lessons_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = MessageTemplates.get('personal_lessons_1')
    link = await ExternalLink.objects.aget(source=LinkSources.FORM_PERSONAL_LESSONS)
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


async def handle_reminder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not update.callback_query:
        return 'AWAIT_REMINDER_CHOICE'
    if update.callback_query.data == 'welcome_choice':
        return await start(update, context)
    elif update.callback_query.data == 'want_to_club':
        return await speak_club_start(update, context)
    elif update.callback_query.data == 'question':
        tg_link = f'https://web.telegram.org/#{chat_id}'
        username = update.effective_chat.username
        await context.bot.send_message(
            chat_id=chat_id,
            text=MessageTemplates.get('need_feedback')
        )
        admins_text = f'У пользователя @{username} есть вопросы о школе\nСсылка: {tg_link}'
        send_tg_message_to_admins(admins_text)
        return 'START'
    return 'START'


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
        'START_AFTER_CLUB_PAYMENT': start,
        'START_AFTER_GROUP_LESSONS': start,
        'WELCOME_CHOICE': handle_welcome_choice,
        'SPEAK_CLUB_LEVEL_CHOICE': handle_speak_club_level_choice,
        'LOWER_LEVEL_CHOICE': handle_lower_level_choice,
        'AWAIT_LEVEL_TEST_CONFIRMATION': handle_level_test_confirmation,
        'TEACHER_PAGINATION': teacher_pagination,
        'AWAIT_SUBSCRIPTION_ACTION': handle_subscription_action,
        'USER_SUBSCRIPTIONS_CHOICE': handle_user_subscriptions_choice,
        'AWAIT_REMINDER_CHOICE': handle_reminder_choice,
    }

    state_handler = states_function[user_state]
    next_state = await state_handler(update, context)
    context.user_data['user'].state = next_state
    await context.user_data['user'].asave()


async def reload_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.user_data.get('user'):
        context.user_data['user'], _ = await User.objects.prefetch_related('subscriptions').aget_or_create(
            chat_id=chat_id,
            defaults={
                'username': update.effective_chat.username
            }
        )
    if context.user_data['user'].is_superuser:
        if update.message.text == '!reload_teachers':
            await MessageTeachers.load_teachers(context)
            await context.bot.send_message(
                chat_id=chat_id,
                text='Учителя обновлены успешно',
            )
        elif update.message.text == '!reload_templates':
            await MessageTemplates.load_templates(context)
            await context.bot.send_message(
                chat_id=chat_id,
                text='Шаблоны сообщений обновлены успешно',
            )


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
    job_queue.run_repeating(send_reminders_hourly,
                            interval=timedelta(hours=1), first=1)

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
