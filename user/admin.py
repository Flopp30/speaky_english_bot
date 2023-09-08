from django.contrib import admin

from .models import User, Teacher
# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'chat_id', 'username', 'last_visit_time', 'registration_datetime', 'first_sub_date', 'is_active'
    )
    list_filter = ('last_visit_time', 'registration_datetime', 'first_sub_date', 'is_active',)
    ordering = ('-id', 'last_visit_time')
    list_per_page = 20
    search_fields = ('username',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'role', 'is_active'
    )
    list_filter = ('role', 'is_active')
    ordering = ('-id',)
    list_per_page = 20
    search_fields = ('name', 'role', 'description')
