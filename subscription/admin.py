from django.contrib import admin

from utils.admin_actions import export_to_csv
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'is_active', 'product', 'user', 'is_auto_renew', 'sub_start_date', 'unsub_date')
    list_filter = ('is_active', 'sub_start_date', 'unsub_date', 'product')
    list_select_related = 'user', 'product'
    actions = [export_to_csv]
    ordering = ('-id', 'is_active', 'product__name', 'user__username')
    list_per_page = 20
    search_fields = ('product__name', 'user__username', 'sub_start_date', 'unsub_date')
