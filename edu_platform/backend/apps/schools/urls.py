from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ApplicationManageViewSet, RegionListView, SchoolApplicationView, SchoolSearchView

router = SimpleRouter()
router.register(r'applications/manage', ApplicationManageViewSet, basename='school-applications-manage')

urlpatterns = [
    path('', SchoolSearchView.as_view(), name='school-search'),
    path('regions/', RegionListView.as_view(), name='school-regions'),
    path('applications/', SchoolApplicationView.as_view(), name='school-applications'),
    path('', include(router.urls)),
]
