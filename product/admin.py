from django.contrib import admin

from utils.admin_actions import export_to_csv
from .models import Product, ExternalLink, SalesAvailability


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'price', 'currency', 'description'
    )
    actions = [export_to_csv]
    list_filter = ('price', 'currency')
    ordering = ('-id', 'price')
    list_per_page = 20
    search_fields = ('id', 'name', 'price', 'currency', 'description')


@admin.register(ExternalLink)
class ExternalLinkAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'source', 'link', )
    list_filter = ('source',)
    actions = [export_to_csv]
    ordering = ('-id',)
    list_per_page = 20
    search_fields = ('id', 'source', 'link',)


@admin.register(SalesAvailability)
class SalesAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wednesday_upper', 'thursday_upper', )
    ordering = ('-id',)
