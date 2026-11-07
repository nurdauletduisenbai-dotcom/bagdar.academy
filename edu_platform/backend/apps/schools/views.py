from django.db.models import Count, F, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import applications
from .models import Region, School, SchoolApplication
from .serializers import ManagedApplicationSerializer, RegionSerializer, SchoolApplicationSerializer, SchoolSerializer


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


@extend_schema(tags=['schools'])
class SchoolApplicationView(APIView):
    """Заявка на подключение школы (без входа). Рассматривает суперпользователь в Django admin."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_form'

    @extend_schema(summary='Подать заявку на подключение школы (публично)', request=SchoolApplicationSerializer,
                   responses={201: None})
    def post(self, request):
        serializer = SchoolApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applications.submit(dict(serializer.validated_data))
        return Response(status=status.HTTP_201_CREATED)


class IsSuperuser(permissions.BasePermission):
    message = 'Доступно только суперпользователю платформы.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


@extend_schema(tags=['schools'])
class ApplicationManageViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                               viewsets.GenericViewSet):
    """Заявки школ на сайте для суперпользователя: просмотр, правка данных, решение."""
    permission_classes = [permissions.IsAuthenticated, IsSuperuser]
    serializer_class = ManagedApplicationSerializer
    filterset_fields = ['status', 'org_type', 'is_claim']
    search_fields = ['school__name', 'school__name_ru', 'contact_name', 'email', 'phone', 'bin']
    http_method_names = ['get', 'patch', 'post']

    def get_queryset(self):
        return SchoolApplication.objects.select_related('school__region', 'reviewed_by').order_by(
            'status', '-created_at')

    def _decide(self, request, fn, **result):
        app = self.get_object()
        note = request.data.get('review_note')
        if isinstance(note, str):
            app.review_note = note.strip()
            app.save(update_fields=['review_note', 'updated_at'])
        outcome = fn(app, request.user)
        app.refresh_from_db()
        data = ManagedApplicationSerializer(app, context={'request': request}).data
        if isinstance(outcome, dict):
            data['result'] = {'invited': outcome['invited'], 'org_id': outcome['org'].id, 'org_name': outcome['org'].name}
        return Response(data)

    @extend_schema(summary='Одобрить: организация школы + заявитель — администратор', request=None)
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, applications.approve)

    @extend_schema(summary='Отклонить (письмо с review_note)')
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if self.get_object().status == SchoolApplication.Status.APPROVED:
            return Response({'detail': 'Одобренную заявку отклонить нельзя.'}, status=status.HTTP_400_BAD_REQUEST)
        return self._decide(request, applications.reject)

    @extend_schema(summary='Запросить уточнения (письмо с review_note)')
    @action(detail=True, methods=['post'], url_path='request-info')
    def request_info(self, request, pk=None):
        if self.get_object().status == SchoolApplication.Status.APPROVED:
            return Response({'detail': 'Заявка уже одобрена.'}, status=status.HTTP_400_BAD_REQUEST)
        return self._decide(request, applications.request_info)

    @extend_schema(summary='Сколько заявок в каждом статусе (для бейджа в меню)')
    @action(detail=False, methods=['get'])
    def summary(self, request):
        counts = dict(SchoolApplication.objects.values_list('status').annotate(n=Count('id')))
        return Response({s: counts.get(s, 0) for s in SchoolApplication.Status.values})
