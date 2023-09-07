from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'payment_service_id', 'payment_service', 'amount', 'created_at', 'updated_at', 'user'
    )
    list_filter = ('created_at', 'updated_at', 'user', 'payment_service')
    ordering = ('-pk', 'created_at', 'updated_at', 'user')
    list_per_page = 20
    search_fields = ('id', 'status', 'payment_service_id', 'payment_service', 'amount')
