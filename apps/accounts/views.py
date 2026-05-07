from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .models import User
from apps.exams.models import ExamAttempt, Exam

def home(request):
    featured_exams = Exam.objects.filter(
        is_active=True,
        is_released=True,
        visibility='PUBLIC',
    ).order_by('-created_at')[:3]
    return render(request, 'accounts/home.html', {'exams': featured_exams})

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to ExamFlow.")
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.role == User.Role.ADMIN:
            return redirect('admin_dashboard_home')
        return redirect('home')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            user.save()
            login(request, user)
            remember = request.POST.get('remember_me', False)
            if not remember:
                request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next')
            if user.is_superuser or user.role == User.Role.ADMIN:
                return redirect('admin_dashboard_home')
            return redirect(next_url or 'home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def profile(request):
    attempts = ExamAttempt.objects.filter(user=request.user)
    completed_attempts = attempts.filter(status='SUBMITTED')
    total_exams = completed_attempts.count()
    avg_score = 0
    pass_rate = 0
    if total_exams > 0:
        avg_score = sum(a.percentage for a in completed_attempts) / total_exams
        passed = completed_attempts.filter(is_passed=True).count()
        pass_rate = (passed / total_exams) * 100

    context = {
        'total_exams': total_exams,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
        'recent_attempts': attempts.order_by('-started_at')[:5]
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def exam_history(request):
    attempts = ExamAttempt.objects.filter(user=request.user).order_by('-started_at')
    return render(request, 'accounts/exam_history.html', {'attempts': attempts})
