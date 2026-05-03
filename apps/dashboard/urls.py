from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('admin/', views.admin_dashboard_home, name='admin_dashboard_home'),
    path('exams/', views.dashboard_exams, name='dashboard_exams'),
    path('admin/exams/', views.admin_dashboard_exams, name='admin_dashboard_exams'),
    path('exams/create/', views.ExamCreateView.as_view(), name='dashboard_exam_create'),
    path('exams/<int:pk>/edit/', views.ExamUpdateView.as_view(), name='dashboard_exam_edit'),
    path('exams/<int:pk>/delete/', views.ExamDeleteView.as_view(), name='dashboard_exam_delete'),
    path('exams/<int:pk>/release/', views.dashboard_exam_release, name='dashboard_exam_release'),
    path('exams/<int:exam_id>/attendees/', views.dashboard_exam_attendees, name='dashboard_exam_attendees'),
    path('exams/<int:exam_id>/attendees/export/', views.dashboard_exam_attendees_export, name='dashboard_exam_attendees_export'),
    path('exams/<int:exam_id>/questions/', views.dashboard_questions, name='dashboard_questions'),
    path('exams/<int:exam_id>/questions/create/', views.QuestionCreateView.as_view(), name='dashboard_question_create'),
    path('questions/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='dashboard_question_edit'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='dashboard_question_delete'),
    
    path('categories/', views.dashboard_categories, name='dashboard_categories'),
    path('admin/categories/', views.admin_dashboard_categories, name='admin_dashboard_categories'),
    path('categories/request/', views.dashboard_category_request_create, name='dashboard_category_request_create'),
    path('categories/requests/<int:pk>/<str:action>/', views.dashboard_category_request_review, name='dashboard_category_request_review'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='dashboard_category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='dashboard_category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='dashboard_category_delete'),
    
    path('users/', views.dashboard_users, name='dashboard_users'),
    path('admin/users/', views.admin_dashboard_users, name='admin_dashboard_users'),
    path('users/create/', views.DashboardUserCreateView.as_view(), name='dashboard_user_create'),
    path('users/<int:pk>/edit/', views.DashboardUserUpdateView.as_view(), name='dashboard_user_edit'),
]
