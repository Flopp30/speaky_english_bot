from django.db import models

from utils.models import NOT_NULLABLE, NULLABLE


class Product(models.Model):
    name = models.CharField(verbose_name='Название продукта', max_length=128, **NOT_NULLABLE)
    price = models.FloatField(verbose_name='Цена', **NOT_NULLABLE, default=0)
    currency = models.CharField(verbose_name='Валюта', max_length=128, **NOT_NULLABLE, default='RUB')
    description = models.TextField(verbose_name='Описание продукта', **NULLABLE)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
