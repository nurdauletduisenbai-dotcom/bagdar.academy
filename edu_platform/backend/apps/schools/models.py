from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Region(TimeStampedModel):
    """Область или город республиканского значения (17 областей + Астана, Алматы, Шымкент)."""
    code = models.CharField('Код ISO 3166-2', max_length=10, unique=True)
    name_ru = models.CharField('Название (рус)', max_length=120)
    name_kk = models.CharField('Название (каз)', max_length=120)
    is_city = models.BooleanField('Город республиканского значения', default=False)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'regions'
        ordering = ['order', 'name_ru']
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'

    def __str__(self):
        return self.name_ru


class SchoolQuerySet(models.QuerySet):
    def visible(self):
        """То, что видно в поиске при регистрации: одобренное и не скрытое."""
        return self.filter(is_approved=True, is_active=True)


class School(TimeStampedModel):
    """
    Справочник учебных заведений Казахстана для выбора при регистрации.
    Это НЕ организация на платформе: если школа подключена, она связана с Organization.
    """

    class Kind(models.TextChoices):
        SCHOOL = 'school', 'Общеобразовательная школа'
        GYMNASIUM = 'gymnasium', 'Гимназия'
        LYCEUM = 'lyceum', 'Лицей'
        SPECIALIZED = 'specialized', 'Специализированная школа (НИШ, РФМШ…)'
        COLLEGE = 'college', 'Колледж'
        CENTER = 'center', 'Учебный центр'
        EXTRA = 'extra', 'Доп. образование (музыка, искусство, спорт)'
        CLUB = 'club', 'Кружок / секция'
        OTHER = 'other', 'Другое'

    class Source(models.TextChoices):
        OSM = 'osm', 'OpenStreetMap'
        IMPORT = 'import', 'Импорт файла'
        ADMIN = 'admin', 'Добавлено администратором'
        USER = 'user', 'Добавлено пользователем'

    name = models.CharField('Название', max_length=255)
    name_kk = models.CharField('Название (каз)', max_length=255, blank=True)
    name_ru = models.CharField('Название (рус)', max_length=255, blank=True)
    kind = models.CharField('Тип', max_length=20, choices=Kind.choices, default=Kind.SCHOOL)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='schools', verbose_name='Регион')
    locality = models.CharField('Населённый пункт', max_length=120, blank=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='directory_schools', verbose_name='Организация на платформе',
                                     help_text='Если школа подключена — ученики при регистрации попадают в неё.')
    is_approved = models.BooleanField('Одобрено', default=True,
                                      help_text='Добавленные пользователями школы ждут проверки и не видны в поиске.')
    is_active = models.BooleanField('Показывать', default=True)
    source = models.CharField('Источник', max_length=10, choices=Source.choices, default=Source.ADMIN)
    external_id = models.CharField('Внешний ID', max_length=64, unique=True, null=True, blank=True,
                                   help_text='Например osm:way/123 — для повторного импорта без дублей.')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='added_schools', verbose_name='Кто добавил')

    objects = SchoolQuerySet.as_manager()

    class Meta:
        db_table = 'schools'
        ordering = ['region__order', 'locality', 'name']
        verbose_name = 'Школа'
        verbose_name_plural = 'Школы'
        indexes = [models.Index(fields=['is_approved', 'is_active', 'region'])]

    def __str__(self):
        return f'{self.name} ({self.locality or self.region})'
