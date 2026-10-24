from django.urls import path

from .views import RegionListView, SchoolSearchView

urlpatterns = [
    path('', SchoolSearchView.as_view(), name='school-search'),
    path('regions/', RegionListView.as_view(), name='school-regions'),
]
