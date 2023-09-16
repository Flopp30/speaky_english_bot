from django.db import models


class Template(models.Model):
    name = models.CharField(
        verbose_name='Название шаблона',
        max_length=100,
        null=False,
    )

    content = models.TextField(
        verbose_name="Текст шаблона",
        default='',
        blank=True,
    )

    class Meta:
        verbose_name = 'Шаблон'
        verbose_name_plural = 'Шаблоны'
