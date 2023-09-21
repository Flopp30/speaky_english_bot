import csv

from django.http import HttpResponse

from product.models import ProductType
from subscription.models import Subscription
from user.models import User
from utils.admin_actions import get_field_verbose_name

report_fields = (
    'id',
    'chat_id',
    'username',
    'last_visit_time',
    'registration_datetime',
    'first_sub_date',
)


def get_personal_lessons_user(admin_model, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="personal_subscribers.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([get_field_verbose_name(User, field_name) for field_name in report_fields] + ['Ссылка на ТГ'])
    subscriptions = (
        Subscription.objects
        .select_related('user', 'product')
        .filter(is_active=True, product__id_name=ProductType.PERSONAL_LESSONS)
        .distinct()
    )
    for sub in subscriptions:
        writer.writerow([getattr(sub.user, field) for field in report_fields] + [sub.user.link])

    return response


get_personal_lessons_user.short_description = "Отчет: участники индивидуальных занятий"


def get_group_lessons_user(admin_model, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="group_subscribers.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([get_field_verbose_name(User, field_name) for field_name in report_fields] + ['Ссылка на ТГ'])
    subscriptions = (
        Subscription.objects
        .select_related('user', 'product')
        .filter(is_active=True, product__id_name=ProductType.GROUP_LESSONS)
        .distinct()
    )
    for sub in subscriptions:
        writer.writerow([getattr(sub.user, field) for field in report_fields] + [sub.user.link])

    return response


get_group_lessons_user.short_description = "Отчет: участники групповых занятий"


def get_speak_clubs_user(admin_model, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="data.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([get_field_verbose_name(User, field_name) for field_name in report_fields] + ['Ссылка на ТГ'])
    subscriptions = (
        Subscription.objects
        .select_related('user', 'product')
        .filter(is_active=True, product__id_name=ProductType.SPEAKY_CLUB)
        .distinct()
    )
    for sub in subscriptions:
        writer.writerow([getattr(sub.user, field) for field in report_fields] + [sub.user.link])

    return response


get_speak_clubs_user.short_description = "Отчет: участники разговорного клуба"
