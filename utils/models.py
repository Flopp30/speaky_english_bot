NULLABLE = {'null': True, 'blank': True}
NOT_NULLABLE = {'null': False, 'blank': False}


class MessageTemplates:
    templates: dict[str, str] = {}
    default_message: str = 'Нет шаблона {key}'

    @classmethod
    def get(cls, key):
        return cls.templates.get(key, cls.default_message.format(key=key))


class MessageTeachers:
    teachers: list[dict[str, str]] = []
