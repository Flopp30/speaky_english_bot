from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'product', 'user', 'is_auto_renew', 'sub_start_date', 'unsub_date')
    list_filter = ('sub_start_date', 'unsub_date', 'product')
    ordering = ('-id', 'product', 'user')
    list_per_page = 20
    search_fields = ('product', 'user', 'sub_start_date', 'unsub_date')
