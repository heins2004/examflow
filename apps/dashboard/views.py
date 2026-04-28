from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from apps.exams.models import Exam, ExamAttempt, Category, Question
from apps.accounts.models import User
from .forms import (
    CategoryForm,
    DashboardUserCreateForm,
    DashboardUserUpdateForm,
    ExamForm,
    QuestionForm,
)
from django.db.models import Count
from django.utils import timezone


def has_dashboard_access(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.is_staff
        or user.role in {User.Role.ADMIN, User.Role.EXAMINER}
    )


dashboard_access_required = user_passes_test(has_dashboard_access, login_url='login')


def is_admin_user(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.role == User.Role.ADMIN
    )


admin_required = user_passes_test(is_admin_user, login_url='login')


def manageable_exams_for(user):
    if user.is_superuser or user.is_staff or user.role == User.Role.ADMIN:
        return Exam.objects.all()
    return Exam.objects.filter(created_by=user)


def get_manageable_exam_or_404(user, **filters):
    return get_object_or_404(manageable_exams_for(user), **filters)


@login_required
@dashboard_access_required
def dashboard_home(request):
    manageable_exams = manageable_exams_for(request.user)
    attempts = ExamAttempt.objects.filter(exam__in=manageable_exams)
    total_users = User.objects.count()
    active_exams = manageable_exams.filter(is_active=True).count()
    attempts_today = attempts.filter(started_at__date=timezone.now().date()).count()
    completed_attempts = attempts.filter(status='SUBMITTED')
    total_completed = completed_attempts.count()
    pass_rate = 0
    if total_completed > 0:
        pass_rate = (completed_attempts.filter(is_passed=True).count() / total_completed) * 100
        
    return render(request, 'dashboard/home.html', {
        'total_users': total_users,
        'active_exams': active_exams,
        'attempts_today': attempts_today,
        'pass_rate': pass_rate,
        'recent_attempts': attempts.order_by('-started_at')[:5]
    })

@login_required
@dashboard_access_required
def dashboard_exams(request):
    exams = manageable_exams_for(request.user).annotate(attempts_count=Count('attempts')).order_by('-created_at')
    return render(request, 'dashboard/exams.html', {'exams': exams})

@login_required
@dashboard_access_required
def dashboard_categories(request):
    categories = Category.objects.annotate(exams_count=Count('exams')).order_by('-created_at')
    return render(request, 'dashboard/categories.html', {'categories': categories})

@login_required
@admin_required
def dashboard_users(request):
    users = User.objects.annotate(attempts_count=Count('exam_attempts')).order_by('-date_joined')
    return render(request, 'dashboard/users.html', {'users': users})


@method_decorator([login_required, admin_required], name='dispatch')
class DashboardUserCreateView(CreateView):
    model = User
    form_class = DashboardUserCreateForm
    template_name = 'dashboard/user_form.html'
    success_url = reverse_lazy('dashboard_users')


@method_decorator([login_required, admin_required], name='dispatch')
class DashboardUserUpdateView(UpdateView):
    model = User
    form_class = DashboardUserUpdateForm
    template_name = 'dashboard/user_form.html'
    success_url = reverse_lazy('dashboard_users')

@login_required
@dashboard_access_required
def dashboard_questions(request, exam_id):
    exam = get_manageable_exam_or_404(request.user, pk=exam_id)
    questions = exam.questions.prefetch_related('options').all()
    return render(request, 'dashboard/questions.html', {
        'exam': exam,
        'questions': questions,
    })


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class ExamCreateView(CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'dashboard/exam_form.html'
    success_url = reverse_lazy('dashboard_exams')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class ExamUpdateView(UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = 'dashboard/exam_form.html'
    success_url = reverse_lazy('dashboard_exams')

    def get_queryset(self):
        return manageable_exams_for(self.request.user)


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class ExamDeleteView(DeleteView):
    model = Exam
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard_exams')

    def get_queryset(self):
        return manageable_exams_for(self.request.user)


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/category_form.html'
    success_url = reverse_lazy('dashboard_categories')


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/category_form.html'
    success_url = reverse_lazy('dashboard_categories')


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard_categories')


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class QuestionCreateView(CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'dashboard/question_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['exam_queryset'] = manageable_exams_for(self.request.user)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['exam'] = get_manageable_exam_or_404(self.request.user, pk=self.kwargs['exam_id'])
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_exam'] = get_manageable_exam_or_404(self.request.user, pk=self.kwargs['exam_id'])
        return context

    def get_success_url(self):
        return reverse_lazy('dashboard_questions', kwargs={'exam_id': self.object.exam_id})


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class QuestionUpdateView(UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'dashboard/question_form.html'

    def get_queryset(self):
        return Question.objects.filter(exam__in=manageable_exams_for(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['exam_queryset'] = manageable_exams_for(self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_exam'] = self.object.exam
        return context

    def get_success_url(self):
        return reverse_lazy('dashboard_questions', kwargs={'exam_id': self.object.exam_id})


@method_decorator([login_required, dashboard_access_required], name='dispatch')
class QuestionDeleteView(DeleteView):
    model = Question
    template_name = 'dashboard/confirm_delete.html'

    def get_queryset(self):
        return Question.objects.filter(exam__in=manageable_exams_for(self.request.user))

    def get_success_url(self):
        return reverse_lazy('dashboard_questions', kwargs={'exam_id': self.object.exam_id})
