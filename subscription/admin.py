from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'is_active', 'product', 'user', 'is_auto_renew', 'sub_start_date', 'unsub_date')
    list_filter = ('is_active', 'sub_start_date', 'unsub_date', 'product')
    ordering = ('-id', 'is_active', 'product', 'user')
    list_per_page = 20
    search_fields = ('product', 'user', 'sub_start_date', 'unsub_date')
