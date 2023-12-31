from django.db import models

NULLABLE = {'null': True, 'blank': True}
NOT_NULLABLE = {'null': False, 'blank': False}


class User(models.Model):
    chat_id = models.BigIntegerField(
        verbose_name='Chat ID',
        null=False,
        blank=False
    )
    username = models.CharField(
        verbose_name='Ник пользователя',
        max_length=100,
        blank=True,
        null=True,
    )

    state = models.CharField(
        verbose_name='Статус переписки в боте',
        max_length=50,
        default='NEW'
    )

    last_visit_time = models.DateTimeField(
        verbose_name='Время последнего посещения',
        auto_now=True,
    )
    registration_datetime = models.DateTimeField(
        verbose_name='Дата и время регистрации',
        auto_now_add=True,
    )

    first_sub_date = models.DateTimeField(
        verbose_name='Дата первой подписки',
        **NULLABLE,
    )

    is_active = models.BooleanField(
        verbose_name='Активен?',
        **NOT_NULLABLE,
        default=True,
    )

    is_superuser = models.BooleanField(
        verbose_name='Администратор',
        **NOT_NULLABLE,
        default=False,
    )

    def __str__(self) -> str:
        return f"{self.username if self.username else self.chat_id}"

    @property
    def link(self):
        return (
            f"https://web.telegram.org/#{self.chat_id}"
        )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @classmethod
    def fields_to_report(cls):
        return (
            'id',
            'chat_id',
            'username',
            'state',
            'last_visit_time',
            'registration_datetime',
            'first_sub_date',
        )


class Teacher(models.Model):
    name = models.CharField(verbose_name='ФИО', max_length=128, **NOT_NULLABLE)
    role = models.CharField(verbose_name='Роль', max_length=128, **NULLABLE)
    description = models.TextField(
        verbose_name='Описание', default='', **NULLABLE)
    photo = models.ImageField(
        upload_to='teacher_photos/',
        verbose_name="Фотография преподавателя",
        **NOT_NULLABLE,
    )
    is_active = models.BooleanField(
        verbose_name='Активен?', **NOT_NULLABLE, default=True)

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
