from django.db.models import F, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions

from .models import Region, School
from .serializers import RegionSerializer, SchoolSerializer


@extend_schema(tags=['schools'])
class RegionListView(generics.ListAPIView):
    """Области и города республиканского значения — для фильтра при выборе школы."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = None
    serializer_class = RegionSerializer
    queryset = Region.objects.all()

    @extend_schema(summary='Регионы Казахстана (публично)')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=['schools'])
class SchoolSearchView(generics.ListAPIView):
    """Поиск по справочнику школ при регистрации (без входа). Только одобренные и не скрытые."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = SchoolSerializer
    filter_backends = []

    @extend_schema(
        summary='Поиск школы (публично)',
        parameters=[OpenApiParameter('search', str, description='Название или населённый пункт; цифры тоже: «8», «№ 25»'),
                    OpenApiParameter('region', int), OpenApiParameter('kind', str)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = School.objects.visible().select_related('region')
        params = self.request.query_params
        if (region := params.get('region', '')).isdigit():
            qs = qs.filter(region_id=int(region))
        if kind := params.get('kind'):
            qs = qs.filter(kind=kind)
        for word in params.get('search', '').replace('№', ' ').split()[:5]:
            qs = qs.filter(Q(name__icontains=word) | Q(name_kk__icontains=word) | Q(name_ru__icontains=word)
                           | Q(locality__icontains=word))
        # Подключённые к платформе — первыми
        return qs.order_by(F('organization_id').asc(nulls_last=True), 'region__order', 'locality', 'name')
