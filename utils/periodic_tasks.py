import datetime

from telegram.ext import CallbackContext

from payment.models import Payment
from subscription.models import Subscription
from utils.services import create_yoo_auto_payment


async def renew_sub_hourly(context: CallbackContext):
    now = datetime.datetime.now()
    expired_subs = Subscription.objects.select_related('product', 'user').filter(unsub_date__lte=now, is_active=True)
    async for sub in expired_subs:
        if sub.is_auto_renew:
            metadata = {
                "sub_id": sub.id,
                "user_id": sub.user.id,
                "chat_id": sub.user.chat_id,
                "renew": True,
            }
            yoo_payment = create_yoo_auto_payment(sub=sub, product=sub.product, metadata=metadata)
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
