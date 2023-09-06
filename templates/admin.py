from django.contrib import admin

from .models import Template
# Register your models here.


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    pass
