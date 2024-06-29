# notifications/urls.py

from django.urls import path
from .views import index, process_form

urlpatterns = [
    path('', index, name='index'),
    path('process_form/', process_form, name='process_form'),
]
