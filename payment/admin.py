from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'user_', 'amount', 'currency', 'payment_service', 'refund_', 'created_at',
        'updated_at',
    )
    list_select_related = 'user', 'refund'
    list_filter = ('created_at', 'updated_at', 'user', 'currency', 'payment_service')
    ordering = ('-pk', 'created_at', 'updated_at', 'user')
    list_per_page = 20
    search_fields = ('id', 'status', 'payment_service_id', 'payment_service', 'amount', 'currency')

    def user_(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.user.link,
            obj.user,
        )

    user_.short_description = 'Пользователь'

    def refund_(self, obj):
        if obj.updated_at < timezone.now() - relativedelta(years=1):
            return format_html('<span title="Вернуть ДС можно в течении года с момента оплаты. Для детальной '
                               'информации обратитесь в платежную систему">Возврат невозможен</span>')

        if not obj.is_refunded:
            button = (
                f'<button paymentId="{obj.pk}" type="button" class="custom-button refund-btn">Вернуть ДС</button>'
            )
            return format_html(
                button
            )
        return format_html('<span>Возвращен</span>')

    refund_.short_description = 'Возврат'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'user_', 'amount_', 'created_at', 'updated_at'
    )
    list_select_related = 'payment', 'payment__user'
    list_filter = ('created_at', 'updated_at',)
    ordering = ('-pk', 'created_at', 'updated_at')
    list_per_page = 20
    search_fields = ('id', 'status',)

    def user_(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.payment.user.link,
            obj.payment.user,
        )

    user_.short_description = 'Пользователь'

    def amount_(self, obj):
        return obj.payment.amount

    amount_.short_description = 'Сумма'
