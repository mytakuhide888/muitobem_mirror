from django.urls import path
from . import views

app_name = 'webhooks'

urlpatterns = [
    path('threads/', views.threads_webhook, name='threads'),
    path('instagram/', views.instagram_webhook, name='instagram'),
]
