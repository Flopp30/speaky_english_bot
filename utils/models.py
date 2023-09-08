NULLABLE = {'null': True, 'blank': True}
NOT_NULLABLE = {'null': False, 'blank': False}


class MessageTemplates:
    templates: dict[str, str] = {}


class MessageTeachers:
    teachers: list[{str: str}] = []
