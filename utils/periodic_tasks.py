from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from payment.models import Payment
from subscription.models import Subscription
from product.models import ExternalLink, LinkSources
from user.models import User
from utils.models import MessageTemplates
from utils.services import create_yoo_auto_payment


async def renew_sub_hourly(context: CallbackContext):
    now = datetime.now()
    expired_subs = Subscription.objects.select_related(
        'product', 'user').filter(unsub_date__lte=now, is_active=True)
    async for sub in expired_subs:
        if sub.is_auto_renew and sub.verified_payment_id:
            metadata = {
                'product_id': sub.product.id
            }
            yoo_payment = create_yoo_auto_payment(
                sub=sub, product=sub.product, metadata=metadata)
            await Payment.objects.acreate(
                status=yoo_payment.get('status'),
                payment_service_id=yoo_payment.get('id'),
                amount=yoo_payment.get('amount').get('value'),
                currency=yoo_payment.get('amount').get('currency'),
                user=sub.user
            )
        else:
            sub.is_active = False
            await sub.asave()
            await context.bot.send_message(sub.user.chat_id, text=f"Ваша подписка на '{sub.product.name}' закончилась.")


async def send_reminders(context: CallbackContext):
    now = datetime.now()
    unfinished_states = {
        'SPEAK_CLUB_LEVEL_CHOICE': {
            'keyboard': [[InlineKeyboardButton('Вопросов нет, хочу в клуб', callback_data='want_to_club')],
                         [InlineKeyboardButton('Да, есть вопросы', callback_data='question')]],
            'message': MessageTemplates.get('speaky_club_reminder'),
        },
        'TEACHER_PAGINATION': {
            'keyboard': [[InlineKeyboardButton('Вопросов нет, сейчас заполню анкету',
                                               url=await ExternalLink.objects.aget(source=LinkSources.PRIVATE_LESSONS))],
                         [InlineKeyboardButton('Да, есть вопросы', callback_data='question')]],
            'message': MessageTemplates.get('personal_lessons_reminder'),
        },
        'WELCOME_CHOICE': {
            'keyboard': [[InlineKeyboardButton('Вопросов нет, сейчас выберу продукт',
                                               callback_data='welcome_choice')],
                         [InlineKeyboardButton('Да, есть вопросы', callback_data='question')]],
            'message': MessageTemplates.get('welcome_reminder'),
        }
    }
    users = User.objects.filter(last_visit_time__gte=(now - timedelta(days=1)),
                                last_visit_time__lte=(
                                    now - timedelta(hours=23)),
                                state__in=unfinished_states.keys())
    async for user in users:
        await context.bot.send_message(
            chat_id=user.chat_id,
            text=unfinished_states.get(user.state)['message'].format(
                username=user.username),
            reply_markup=InlineKeyboardMarkup(
                unfinished_states.get(user.state)['keyboard']),
        )
        user.state = 'AWAIT_REMINDER_CHOICE'
    await User.objects.abulk_update(users, ['state'])
