from django.urls import path
from . import views

app_name = 'social_webhooks'

urlpatterns = [
    path('instagram/', views.instagram, name='instagram'),
    path('threads/', views.threads, name='threads'),
]
