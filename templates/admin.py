from django.contrib import admin

from .models import Template
# Register your models here.


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'content',
    )
    ordering = ('-id',)
    list_per_page = 30
    search_fields = ('name', 'content')
