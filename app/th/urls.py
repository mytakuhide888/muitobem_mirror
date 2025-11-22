from django.urls import path
from . import views

app_name = 'th'

urlpatterns = [
    path('dashboard/', views.placeholder, name='dashboard'),
    path('insights/', views.placeholder, name='insights'),
    path('inbox/', views.placeholder, name='inbox'),
    path('automation/reactions/', views.placeholder, name='automation_reactions'),
    path('automation/icebreakers/', views.placeholder, name='automation_icebreakers'),
    path('broadcasts/', views.placeholder, name='broadcasts'),
    path('posts/', views.posts, name='posts'),
    path('posts/import/', views.posts_import, name='posts_import'),
    path('posts/sync/', views.posts_sync, name='posts_sync'),
    path('scheduled/', views.scheduled, name='scheduled'),
    path('scheduled/<int:pk>/approve/', views.scheduled_approve, name='scheduled_approve'),
    path('lotteries/', views.placeholder, name='lotteries'),
    path('surveys/', views.placeholder, name='surveys'),
    path('users/', views.placeholder, name='users'),
    path('tags/', views.placeholder, name='tags'),
    path('attributes/', views.placeholder, name='attributes'),
    path('archive/', views.placeholder, name='archive'),
    path('integration/', views.placeholder, name='integration'),
    path('auto-replies/', views.placeholder, name='auto_replies'),
    path('status/', views.placeholder, name='status'),
]
