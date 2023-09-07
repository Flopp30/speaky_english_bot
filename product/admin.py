from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'price_rub', 'price_usd', 'description'
    )
    list_filter = ('price_rub',)
    ordering = ('-id', 'price_rub')
    list_per_page = 20
    search_fields = ('id', 'name', 'price_rub', 'price_usd', 'description')
