from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('posts/import/', views.import_posts, name='post-import'),
    path('posts/sync/', views.sync_posts, name='post-sync'),
    path('scheduled/approve/<int:pk>/', views.approve_scheduled, name='scheduled-approve'),
]
