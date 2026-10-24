import re

from rest_framework import serializers

from .models import Region, School, SchoolApplication


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ('id', 'code', 'name_ru', 'name_kk', 'is_city')


class SchoolSerializer(serializers.ModelSerializer):
    region_name_ru = serializers.CharField(source='region.name_ru', read_only=True)
    region_name_kk = serializers.CharField(source='region.name_kk', read_only=True)
    on_platform = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ('id', 'name', 'name_kk', 'name_ru', 'kind', 'region', 'region_name_ru', 'region_name_kk',
                  'locality', 'on_platform')

    def get_on_platform(self, obj) -> bool:
        return bool(obj.organization_id)


class NewSchoolSerializer(serializers.Serializer):
    """«Моей школы нет в списке» — ученик вводит своё; попадает на проверку администратору."""
    name = serializers.CharField(max_length=255, min_length=3)
    kind = serializers.ChoiceField(choices=School.Kind.choices, default=School.Kind.SCHOOL)
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all())
    locality = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')

    def validate_name(self, value):
        return ' '.join(value.split())


class SchoolApplicationSerializer(serializers.ModelSerializer):
    """Заявка на подключение школы: школа из справочника или своя + контакты заявителя."""
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.visible(),
                                                   required=False, allow_null=True)
    new_school = NewSchoolSerializer(required=False, allow_null=True)
    consent = serializers.BooleanField(write_only=True)

    class Meta:
        model = SchoolApplication
        fields = ('school_id', 'new_school', 'org_type', 'contact_name', 'position', 'email', 'phone',
                  'students_count', 'bin', 'message', 'language', 'consent')

    def validate_phone(self, value):
        if not 10 <= len(re.sub(r'\D', '', value)) <= 15:
            raise serializers.ValidationError('Укажите номер телефона, например +7 700 000 00 00.')
        return value.strip()

    def validate_bin(self, value):
        value = re.sub(r'\s', '', value or '')
        if value and not re.fullmatch(r'\d{12}', value):
            raise serializers.ValidationError('БИН — 12 цифр.')
        return value

    def validate_contact_name(self, value):
        value = ' '.join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError('Укажите ФИО.')
        return value

    def validate_language(self, value):
        return value if value in ('kk', 'ru') else ''

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError('Нужно согласие на обработку персональных данных.')
        return value

    def validate(self, attrs):
        attrs.pop('consent', None)
        if bool(attrs.get('school')) == bool(attrs.get('new_school')):
            raise serializers.ValidationError({'school_id': 'Выберите школу из списка или добавьте свою — одно из двух.'})
        attrs['email'] = attrs['email'].lower()
        return attrs


# ---------- Рассмотрение заявок суперпользователем на сайте ----------

class ManagedSchoolSerializer(serializers.ModelSerializer):
    region_name_ru = serializers.CharField(source='region.name_ru', read_only=True)
    region_name_kk = serializers.CharField(source='region.name_kk', read_only=True)
    admins = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ('id', 'name', 'name_kk', 'name_ru', 'kind', 'region', 'region_name_ru', 'region_name_kk',
                  'locality', 'is_approved', 'is_active', 'source', 'organization', 'admins')

    def get_admins(self, obj) -> list[str]:
        from apps.organizations.models import OrgMembership
        if not obj.organization_id:
            return []
        return list(OrgMembership.objects.filter(org_id=obj.organization_id, role='admin', is_active=True)
                    .values_list('user__email', flat=True))


class SchoolEditSerializer(serializers.Serializer):
    """Правка карточки школы прямо из заявки (опечатки, регион, тип)."""
    name = serializers.CharField(max_length=255, min_length=3, required=False)
    name_kk = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ru = serializers.CharField(max_length=255, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=School.Kind.choices, required=False)
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False)
    locality = serializers.CharField(max_length=120, required=False, allow_blank=True)


class ManagedApplicationSerializer(serializers.ModelSerializer):
    school = ManagedSchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True,
                                                   required=False, help_text='Заменить на другую школу справочника')
    school_edit = SchoolEditSerializer(write_only=True, required=False)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, default='')

    class Meta:
        model = SchoolApplication
        fields = ('id', 'status', 'school', 'school_id', 'school_edit', 'org_type', 'contact_name', 'position',
                  'email', 'phone', 'students_count', 'bin', 'message', 'language', 'is_claim', 'review_note',
                  'reviewed_by_email', 'reviewed_at', 'created_at')
        read_only_fields = ('id', 'status', 'language', 'is_claim', 'reviewed_by_email', 'reviewed_at', 'created_at')

    validate_phone = SchoolApplicationSerializer.validate_phone
    validate_bin = SchoolApplicationSerializer.validate_bin
    validate_contact_name = SchoolApplicationSerializer.validate_contact_name

    def validate_email(self, value):
        return value.lower()

    def validate(self, attrs):
        if self.instance and self.instance.status == SchoolApplication.Status.APPROVED and \
                set(attrs) - {'review_note'}:
            raise serializers.ValidationError('Заявка уже одобрена — данные не меняются.')
        return attrs

    def update(self, instance, validated_data):
        school_edit = validated_data.pop('school_edit', None)
        instance = super().update(instance, validated_data)
        if school_edit:
            school = instance.school
            for field, value in school_edit.items():
                setattr(school, field, ' '.join(value.split()) if field.startswith('name') else value)
            school.save()
        return instance
