from django.urls import path
from APPS.rrhh.views import PersonalListView, PersonalCreateView

app_name = 'rrhh'

urlpatterns = [
    path('personal/', PersonalListView.as_view(), name='personal_list'),
    path('personal/crear/', PersonalCreateView.as_view(), name='personal_create'),
]
