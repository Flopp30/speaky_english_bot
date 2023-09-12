from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'price', 'currency', 'description'
    )
    list_filter = ('price', 'currency')
    ordering = ('-id', 'price')
    list_per_page = 20
    search_fields = ('id', 'name', 'price', 'currency', 'description')
