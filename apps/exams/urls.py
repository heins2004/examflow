from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('<slug:slug>/', views.exam_detail, name='exam_detail'),
    path('<slug:slug>/start/', views.exam_start, name='exam_start'),
    path('<slug:slug>/attempt/<int:id>/', views.exam_attempt, name='exam_attempt'),
    path('<slug:slug>/result/<int:id>/', views.exam_result, name='exam_result'),
    path('<slug:slug>/certificate/<int:id>/', views.exam_certificate, name='exam_certificate'),
    path('<slug:slug>/leaderboard/', views.exam_leaderboard, name='exam_leaderboard'),
]
