from django.contrib import admin
from django.utils.html import format_html

from .models import User, Teacher
# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'chat_id', 'username_', 'send_message_', 'last_visit_time', 'registration_datetime', 'first_sub_date',
        'is_active', 'state'
    )
    list_filter = ('last_visit_time', 'registration_datetime', 'first_sub_date', 'is_active', 'state')
    ordering = ('-id', 'last_visit_time')
    list_per_page = 20
    search_fields = ('username',)

    def username_(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.link,
            obj,
        )
    username_.short_description = 'Имя пользователя'

    def send_message_(self, obj):
        return format_html(
            f'<button userId={obj.pk} type="button" class="custom-button send-msg-btn">Сообщение</button>'
        )
    send_message_.short_description = 'Отправить сообщение'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'role', 'is_active'
    )
    list_filter = ('role', 'is_active')
    ordering = ('-id',)
    list_per_page = 20
    search_fields = ('name', 'role', 'description')
