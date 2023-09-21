from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from product.models import ProductType
from subscription.models import Subscription
from utils.admin_actions import export_to_csv
from .admin_actions import get_personal_lessons_user, get_group_lessons_user, get_speak_clubs_user
from .models import User, Teacher


class PersonalSubscriberFilter(admin.SimpleListFilter):
    title = _('Подписан на индивидуальные занятия')
    parameter_name = 'is_personal_subscriber'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        user_ids = (
            Subscription.objects
            .select_related('user', 'product')
            .filter(is_active=True, product__id_name=ProductType.PERSONAL_LESSONS)
            .values('user_id')
            .distinct()
        )
        if self.value() == 'yes':
            return queryset.filter(id__in=user_ids)
        if self.value() == 'no':
            return queryset.exclude(id__in=user_ids)


class GroupSubscriberFilter(admin.SimpleListFilter):
    title = _('Подписан на групповые занятия')
    parameter_name = 'is_group_subscriber'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        user_ids = (
            Subscription.objects
            .select_related('user', 'product')
            .filter(is_active=True, product__id_name=ProductType.GROUP_LESSONS)
            .values('user_id')
            .distinct()
        )
        if self.value() == 'yes':
            return queryset.filter(id__in=user_ids)
        if self.value() == 'no':
            return queryset.exclude(id__in=user_ids)


class SpeakClubSubscriberFilter(admin.SimpleListFilter):
    title = _('Подписан на разговорный клуб')
    parameter_name = 'is_speak_subscriber'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        user_ids = (
            Subscription.objects
            .select_related('user', 'product')
            .filter(is_active=True, product__id_name=ProductType.SPEAKY_CLUB)
            .values('user_id')
            .distinct()
        )
        if self.value() == 'yes':
            return queryset.filter(id__in=user_ids)
        if self.value() == 'no':
            return queryset.exclude(id__in=user_ids)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'chat_id', 'username', 'link_', 'send_message_', 'last_visit_time', 'registration_datetime',
        'first_sub_date', 'state'
    )
    list_filter = (
        PersonalSubscriberFilter, GroupSubscriberFilter, SpeakClubSubscriberFilter, 'last_visit_time',
        'registration_datetime',
        'first_sub_date', 'state'
    )
    actions = [
        export_to_csv,
        get_personal_lessons_user,
        get_group_lessons_user,
        get_speak_clubs_user,
    ]
    ordering = ('-id', 'username', 'last_visit_time')
    list_per_page = 20
    list_prefetch_related = ['subscriptions', ]
    search_fields = ('username', 'state')

    def link_(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.link,
            obj,
        )

    link_.short_description = 'TG link'

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
