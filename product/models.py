from django.db import models

from utils.models import NOT_NULLABLE, NULLABLE


class Product(models.Model):
    id = models.IntegerField(verbose_name='id', primary_key=True)
    price_rub = models.FloatField(verbose_name='Цена в рублях', **NOT_NULLABLE)
    price_usd = models.FloatField(verbose_name='Цена в долларах', **NULLABLE)
    description = models.TextField(verbose_name='Описание продукта', **NULLABLE)
