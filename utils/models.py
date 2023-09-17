from templates.models import Template
from user.models import Teacher


NULLABLE = {'null': True, 'blank': True}
NOT_NULLABLE = {'null': False, 'blank': False}


class MessageTemplates:
    templates: dict[str, str] = {}
    default_message: str = 'Нет шаблона {key}'

    @classmethod
    def get(cls, key):
        return cls.templates.get(key, cls.default_message.format(key=key))

    @classmethod
    async def load_templates(cls, context):
        cls.templates = {}
        async for template in Template.objects.all():
            cls.templates[template.name] = (
                template.content
                .replace('<div>', '').replace('</div>', '')
                .replace('<br />', '').replace('&nbsp;', '')
                .replace('<p>', '').replace('</p>', '')
            )


class MessageTeachers:
    teachers: list[dict[str, str]] = []

    @classmethod
    async def load_teachers(cls, *args, **kwargs):
        cls.teachers = []
        async for teacher in Teacher.objects.filter(is_active=True):
            photo_path = teacher.photo.path
            description = (
                teacher.description
                .replace('<div>', '').replace('</div>', '')
                .replace('<br />', '').replace('&nbsp;', '')
                .replace('<p>', '').replace('</p>', '')
            )
            caption = (
                f"<b>{teacher.name}</b>\n<i>{teacher.role}</i>\n\n{description}")

            cls.teachers.append(
                {
                    "photo_path": photo_path,
                    "caption": caption
                }
            )
