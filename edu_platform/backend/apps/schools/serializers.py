from rest_framework import serializers

from .models import Region, School


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
