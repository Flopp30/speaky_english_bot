import csv

from django.core.exceptions import FieldDoesNotExist
from django.http import HttpResponse


def get_field_verbose_name(model, field_name):
    try:
        field = model._meta.get_field(field_name)
        return field.verbose_name
    except FieldDoesNotExist:
        return field_name


def export_to_csv(admin_model, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="data.csv"'

    writer = csv.writer(response, delimiter=';')
    fields = [field_name for field_name in queryset.model.fields_to_report()]
    writer.writerow([get_field_verbose_name(queryset.model, field_name) for field_name in fields])

    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in fields])

    return response


export_to_csv.short_description = "Отчет: скачать CSV"
