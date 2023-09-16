from django.db.models.signals import post_save
from django.dispatch import receiver

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
    def load_templates(cls):
        cls.templates = {}
        for template in Template.objects.all():
            cls.templates[template.name] = (
                template.content
                .replace('<div>', '').replace('</div>', '')
                .replace('<br />', '').replace('&nbsp;', '')
                .replace('<p>', '').replace('</p>', '')
            )


@receiver(post_save, sender=Template)
def reloadModels(sender, **kwargs):
    MessageTemplates.load_templates()


class MessageTeachers:
    teachers: list[dict[str, str]] = []

    @classmethod
    def load_teachers(cls):
        cls.teachers = []
        for teacher in Teacher.objects.filter(is_active=True):
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


@receiver(post_save, sender=Teacher)
def reloadModels(sender, **kwargs):
    MessageTeachers.load_teachers()
