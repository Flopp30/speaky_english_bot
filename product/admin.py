from django.contrib import admin

from .models import Product, ExternalLink


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'price', 'currency', 'description'
    )
    list_filter = ('price', 'currency')
    ordering = ('-id', 'price')
    list_per_page = 20
    search_fields = ('id', 'name', 'price', 'currency', 'description')


@admin.register(ExternalLink)
class ExternalLinkAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'source', 'link', )
    list_filter = ('source',)
    ordering = ('-id',)
    list_per_page = 20
    search_fields = ('id', 'source', 'link',)
