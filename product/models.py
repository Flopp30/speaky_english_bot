from django.db import models

from utils.models import NOT_NULLABLE, NULLABLE


class ProductType(models.TextChoices):
    SPEAKY_CLUB = 'speaky_club'
    GROUP_LESSONS = 'group_lessons'
    PERSONAL_LESSONS = 'personal_lessons'


class Product(models.Model):
    id_name = models.CharField(
        verbose_name='Название продукта для бота',
        max_length=50,
        **NOT_NULLABLE,
        unique=True,
        choices=ProductType.choices
    )
    name = models.CharField(
        verbose_name='Название продукта для отображения', max_length=128, **NOT_NULLABLE)
    price = models.FloatField(verbose_name='Цена', **NOT_NULLABLE, default=0)
    currency = models.CharField(
        verbose_name='Валюта', max_length=128, **NOT_NULLABLE, default='RUB')
    description = models.TextField(
        verbose_name='Описание продукта', **NULLABLE)

    def __str__(self):
        return f"Продукт {self.name}"

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    @classmethod
    def fields_to_report(cls):
        return (
            'id',
            'name',
            'price',
            'currency',
            'description',
        )


class LinkSources(models.TextChoices):
    SPEAK_CLUB_UPPER = 'Разговорный клуб High Inter / Upper'
    SPEAK_CLUB_ADV = 'Разговорный клуб Advanced'
    PRIVATE_LESSONS = 'Индивидуальные занятия'
    GROUP_LESSONS = 'Групповые занятия'


class ExternalLink(models.Model):
    source = models.CharField(
        verbose_name='Что за ссылка?',
        unique=True,
        **NOT_NULLABLE,
        choices=LinkSources.choices,
        max_length=128,
    )
    link = models.CharField(
        verbose_name='Ссылка',
        max_length=128,
        **NOT_NULLABLE,
        unique=False,
    )

    def __str__(self):
        return f"{self.source}"

    class Meta:
        verbose_name = 'Ссылка'
        verbose_name_plural = 'Ссылки'

    @classmethod
    def fields_to_report(cls):
        return (
            'id',
            'source',
            'link',
        )
