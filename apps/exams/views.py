import json
import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from apps.accounts.models import User
from .models import Exam, Category, ExamAccess, ExamAttempt, Question, Option, UserAnswer
from django.db.models import Count


def can_view_exam(user, exam):
    if exam.is_released is False:
        if not user.is_authenticated:
            return False
        if user == exam.created_by or user.role == User.Role.ADMIN or user.is_superuser:
            return True
        return False
    if exam.visibility == 'PUBLIC':
        return True
    if not user.is_authenticated:
        return False
    if user == exam.created_by or user.role == User.Role.ADMIN or user.is_superuser:
        return True
    return ExamAccess.objects.filter(user=user, exam=exam).exists()


def is_exam_available_now(exam):
    now = timezone.now()
    if exam.start_time and now < exam.start_time:
        return False, "This exam has not opened yet."
    if exam.end_time and now > exam.end_time:
        return False, "This exam is closed."
    return True, ""


def has_unlocked_pass_key(request, exam):
    return request.session.get(f"exam-passkey-{exam.id}") is True or not exam.requires_pass_key


def get_completed_attempts_queryset(user, exam):
    attempts = ExamAttempt.objects.filter(user=user, exam=exam).exclude(status='IN_PROGRESS')
    if exam.one_attempt_only:
        return attempts
    return attempts.filter(started_at__date=timezone.localdate())


def exam_list(request):
    exams = Exam.objects.filter(is_active=True, is_released=True, visibility='PUBLIC').order_by('-created_at')
    categories = Category.objects.order_by('name')
    
    cat_slug = request.GET.get('category')
    q = request.GET.get('q')
    
    if cat_slug:
        exams = exams.filter(category__slug=cat_slug)
    if q:
        exams = exams.filter(title__icontains=q)
        
    return render(request, 'exams/exam_list.html', {
        'exams': exams,
        'categories': categories,
        'current_category': cat_slug,
        'search_query': q
    })

@login_required
def exam_join_by_code(request):
    joined_exam = None
    if request.method == 'POST':
        exam_code = (request.POST.get('exam_code') or '').strip().upper()

        exam = Exam.objects.filter(exam_code=exam_code, is_active=True, is_released=True).first()
        if not exam:
            messages.error(request, "No exam was found for that exam code.")
        else:
            ExamAccess.objects.get_or_create(user=request.user, exam=exam)
            joined_exam = exam
            messages.success(request, f"You can now access {exam.title}.")
            return redirect('exam_detail', slug=exam.slug)

    return render(request, 'exams/exam_join.html', {'joined_exam': joined_exam})

def exam_detail(request, slug):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    if not can_view_exam(request.user, exam):
        messages.warning(request, "This exam is not publicly available yet. Use the released exam code or wait for the examiner to release it.")
        return redirect('exam_join')

    pass_key_unlocked = has_unlocked_pass_key(request, exam)
    availability_ok, availability_message = is_exam_available_now(exam)

    if request.method == 'POST' and request.user.is_authenticated:
        entered_pass_key = (request.POST.get('pass_key') or '').strip().upper()
        if exam.requires_pass_key:
            if entered_pass_key == (exam.pass_key or '').upper():
                request.session[f"exam-passkey-{exam.id}"] = True
                pass_key_unlocked = True
                messages.success(request, "Pass key accepted. You can start the exam now.")
            else:
                messages.error(request, "The pass key is incorrect.")

    user_attempts = 0
    completed_attempts = 0
    in_progress_attempt = None
    if request.user.is_authenticated:
        attempt_qs = ExamAttempt.objects.filter(user=request.user, exam=exam)
        user_attempts = attempt_qs.count()
        completed_attempts = get_completed_attempts_queryset(request.user, exam).count()
        in_progress_attempt = attempt_qs.filter(status='IN_PROGRESS').first()
        
    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'user_attempts': user_attempts,
        'completed_attempts': completed_attempts,
        'in_progress_attempt': in_progress_attempt,
        'can_attempt': completed_attempts < exam.max_attempts if (exam.max_attempts > 0 and not exam.one_attempt_only) else completed_attempts < 1 if exam.one_attempt_only else True,
        'has_questions': exam.questions.exists(),
        'pass_key_unlocked': pass_key_unlocked,
        'availability_ok': availability_ok,
        'availability_message': availability_message,
    })

@login_required
def exam_start(request, slug):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only student accounts can take exams.")
        return redirect('exam_detail', slug=slug)

    if not can_view_exam(request.user, exam):
        messages.error(request, "You do not have access to this exam.")
        return redirect('exam_join')

    if exam.requires_pass_key and not has_unlocked_pass_key(request, exam):
        messages.error(request, "Enter the exam pass key before starting.")
        return redirect('exam_detail', slug=slug)

    availability_ok, availability_message = is_exam_available_now(exam)
    if not availability_ok:
        messages.error(request, availability_message)
        return redirect('exam_detail', slug=slug)

    in_progress = ExamAttempt.objects.filter(user=request.user, exam=exam, status='IN_PROGRESS').first()
    if in_progress:
        return redirect('exam_attempt', slug=slug, id=in_progress.id)

    if not exam.questions.exists():
        messages.error(request, "This exam has no questions yet.")
        return redirect('exam_detail', slug=slug)

    completed_attempts = get_completed_attempts_queryset(request.user, exam).count()
    limit_reached = completed_attempts >= 1 if exam.one_attempt_only else exam.max_attempts > 0 and completed_attempts >= exam.max_attempts
    if limit_reached:
        messages.error(request, "You have reached the maximum number of attempts for this exam.")
        return redirect('exam_detail', slug=slug)
        
    attempt = ExamAttempt.objects.create(
        user=request.user,
        exam=exam,
        attempt_number=completed_attempts + 1
    )
    return redirect('exam_attempt', slug=slug, id=attempt.id)

@login_required
def exam_attempt(request, slug, id):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    attempt = get_object_or_404(ExamAttempt, id=id, user=request.user, exam=exam)
    
    if attempt.status != 'IN_PROGRESS':
        return redirect('exam_result', slug=slug, id=attempt.id)
        
    # Calculate remaining time
    time_elapsed = (timezone.now() - attempt.started_at).total_seconds()
    if exam.is_unlimited_time or not exam.duration_minutes:
        time_remaining_seconds = None
    else:
        time_remaining_seconds = max(0, (exam.duration_minutes * 60) - time_elapsed)
        if time_remaining_seconds <= 0:
            return submit_exam_logic(attempt)
        
    if request.method == 'POST':
        if 'ajax' in request.POST or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            # AJAX save logic
            data = json.loads(request.body)
            action = data.get('action')
            if action == 'save_answer':
                q_id = data.get('question_id')
                opt_id = data.get('option_id')
                txt_ans = data.get('text_answer')
                
                question = get_object_or_404(Question, id=q_id, exam=exam)
                user_ans, created = UserAnswer.objects.get_or_create(attempt=attempt, question=question)
                
                if question.question_type in {'FILL_BLANK', 'SHORT_ANSWER'}:
                    user_ans.text_answer = txt_ans
                else:
                    if opt_id:
                        option = get_object_or_404(Option, id=opt_id)
                        user_ans.selected_option = option
                user_ans.save()
                return JsonResponse({'status': 'ok'})
            elif action == 'submit':
                submit_exam_logic(attempt)
                return JsonResponse({'status': 'submitted', 'url': f'/exams/{slug}/result/{id}/'})
                
        # Non-AJAX fallback or final submit
        return submit_exam_logic(attempt)
        
    questions = exam.questions.all().prefetch_related('options')
    if exam.shuffle_questions:
        questions = questions.order_by('?')
        
    # Preload user answers
    saved_answers = UserAnswer.objects.filter(attempt=attempt)
    answered_map = {}
    for ans in saved_answers:
        if ans.question.question_type in {'FILL_BLANK', 'SHORT_ANSWER'}:
            answered_map[ans.question.id] = ans.text_answer
        else:
            if ans.selected_option:
                answered_map[ans.question.id] = ans.selected_option.id
                
    return render(request, 'exams/exam_attempt.html', {
        'exam': exam,
        'attempt': attempt,
        'questions': questions,
        'time_remaining': time_remaining_seconds,
        'answered_map': json.dumps(answered_map)
    })

def submit_exam_logic(attempt):
    attempt.status = 'SUBMITTED'
    attempt.submitted_at = timezone.now()
    time_taken = (attempt.submitted_at - attempt.started_at).total_seconds()
    if attempt.exam.is_unlimited_time or not attempt.exam.duration_minutes:
        attempt.time_taken_seconds = int(time_taken)
    else:
        exam_duration_sec = attempt.exam.duration_minutes * 60
        attempt.time_taken_seconds = min(time_taken, exam_duration_sec)
    
    total_score = 0
    questions = attempt.exam.questions.all()
    user_answers = UserAnswer.objects.filter(attempt=attempt)
    ans_map = {ans.question_id: ans for ans in user_answers}
    
    for q in questions:
        ans = ans_map.get(q.id)
        if not ans:
            continue
            
        marks_obtained = 0
        is_correct = False
        
        if q.question_type in {'FILL_BLANK', 'SHORT_ANSWER'}:
            # Basic text match for now
            correct_opts = q.options.filter(is_correct=True)
            if correct_opts.exists() and ans.text_answer:
                # check if any correct option matches text
                matches = [opt.option_text.lower() for opt in correct_opts]
                if ans.text_answer.strip().lower() in matches:
                    is_correct = True
        else:
            if ans.selected_option and ans.selected_option.is_correct:
                is_correct = True
                
        if is_correct:
            marks_obtained = q.marks
        else:
            if ans.selected_option or ans.text_answer: # They attempted it
                marks_obtained = -float(q.negative_marks)
                
        ans.is_correct = is_correct
        ans.marks_obtained = marks_obtained
        ans.save()
        total_score += marks_obtained
        
    attempt.score = max(0, total_score)
    attempt.percentage = (attempt.score / attempt.exam.total_marks) * 100 if attempt.exam.total_marks > 0 else 0
    attempt.is_passed = attempt.score >= attempt.exam.pass_marks
    attempt.save()
    
    from django.shortcuts import redirect
    return redirect('exam_result', slug=attempt.exam.slug, id=attempt.id)

@login_required
def exam_result(request, slug, id):
    exam = get_object_or_404(Exam, slug=slug)
    attempt = get_object_or_404(ExamAttempt, id=id, user=request.user, exam=exam)
    
    if attempt.status != 'SUBMITTED':
        messages.warning(request, "This exam attempt is not complete.")
        return redirect('exam_attempt', slug=slug, id=id)
        
    total_qs = exam.questions.count()
    user_answers = attempt.user_answers.all()
    
    correct_count = user_answers.filter(is_correct=True).count()
    attempted_ids = [a.question_id for a in user_answers if a.selected_option_id or a.text_answer]
    attempted_count = len(attempted_ids)
    wrong_count = attempted_count - correct_count
    skipped_count = total_qs - attempted_count
    
    grade = 'F'
    p = attempt.percentage
    if p >= 90: grade = 'A'
    elif p >= 80: grade = 'B'
    elif p >= 70: grade = 'C'
    elif p >= 60: grade = 'D'
    
    rank = ExamAttempt.objects.filter(exam=exam, score__gt=attempt.score, status='SUBMITTED').count() + 1
    
    # Detailed review
    review_data = []
    questions = exam.questions.all().prefetch_related('options')
    ans_map = {a.question_id: a for a in user_answers}
    
    for q in questions:
        ans = ans_map.get(q.id)
        review_data.append({
            'question': q,
            'user_answer': ans,
            'is_correct': ans.is_correct if ans else False,
            'marks_obtained': ans.marks_obtained if ans else 0
        })
        
    return render(request, 'exams/exam_result.html', {
        'exam': exam,
        'attempt': attempt,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'skipped_count': skipped_count,
        'grade': grade,
        'rank': rank,
        'review_data': review_data
    })

def exam_leaderboard(request, slug):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    top_attempts = ExamAttempt.objects.filter(exam=exam, status='SUBMITTED').order_by('-score', 'time_taken_seconds')[:10]
    return render(request, 'exams/exam_leaderboard.html', {
        'exam': exam,
        'top_attempts': top_attempts
    })

@login_required
def exam_certificate(request, slug, id):
    exam = get_object_or_404(Exam, slug=slug)
    attempt = get_object_or_404(ExamAttempt, id=id, user=request.user, exam=exam)

    if not exam.is_certification:
        messages.error(request, 'Certificates are only available for certification exams.')
        return redirect('exam_result', slug=slug, id=id)

    if not attempt.is_passed or attempt.status != 'SUBMITTED':
        messages.error(request, 'You need to pass the exam to download the certificate.')
        return redirect('exam_result', slug=slug, id=id)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.utils import ImageReader
    import io

    style_map = {
        'TEMPLATE_1': ((0.10, 0.12, 0.36), (0.42, 0.38, 1.00), "CERTIFICATE OF COMPLETION"),
        'TEMPLATE_2': ((0.09, 0.27, 0.20), (0.90, 0.58, 0.13), "ACHIEVEMENT CERTIFICATE"),
        'TEMPLATE_3': ((0.27, 0.15, 0.08), (0.82, 0.46, 0.18), "CERTIFIED SUCCESS"),
        'TEMPLATE_4': ((0.14, 0.18, 0.31), (0.19, 0.65, 0.75), "MERIT CERTIFICATE"),
        'TEMPLATE_5': ((0.25, 0.11, 0.27), (0.76, 0.29, 0.58), "CERTIFICATE OF MERIT"),
        'TEMPLATE_6': ((0.22, 0.22, 0.22), (0.93, 0.64, 0.18), "EXCELLENCE AWARD"),
        'TEMPLATE_7': ((0.07, 0.26, 0.39), (0.27, 0.72, 0.65), "PROFICIENCY CERTIFICATE"),
        'TEMPLATE_8': ((0.31, 0.13, 0.17), (0.88, 0.31, 0.24), "CERTIFIED COMPLETION"),
        'TEMPLATE_9': ((0.10, 0.32, 0.16), (0.54, 0.73, 0.22), "DISTINCTION CERTIFICATE"),
        'TEMPLATE_10': ((0.17, 0.11, 0.37), (0.34, 0.50, 0.95), "CERTIFICATE OF ACHIEVEMENT"),
    }
    bg_color, accent_color, heading = style_map.get(exam.certificate_template, style_map['TEMPLATE_1'])

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    if exam.certificate_template_upload:
        p.drawImage(ImageReader(exam.certificate_template_upload.path), 0, 0, width=width, height=height)
        p.setFillColorRGB(1, 1, 1)
        p.setStrokeColorRGB(*bg_color)
        p.rect(28, 28, width - 56, height - 56, stroke=1, fill=0)
    else:
        p.setFillColorRGB(*bg_color)
        p.rect(0, 0, width, height, stroke=0, fill=1)
        p.setFillColorRGB(1, 1, 1)
        p.rect(20, 20, width-40, height-40, stroke=1, fill=1)

    p.setFillColorRGB(*bg_color)
    p.setFont("Helvetica-Bold", 40)
    p.drawCentredString(width/2.0, height-100, heading)

    p.setFont("Helvetica", 20)
    p.drawCentredString(width/2.0, height-160, "This is to certify that")

    p.setFont("Helvetica-Bold", 30)
    p.setFillColorRGB(*accent_color)
    p.drawCentredString(width/2.0, height-210, attempt.user.get_full_name() or attempt.user.username)

    p.setFillColorRGB(*bg_color)
    p.setFont("Helvetica", 20)
    p.drawCentredString(width/2.0, height-270, "has successfully completed the exam")

    p.setFont("Helvetica-Bold", 25)
    p.drawCentredString(width/2.0, height-320, exam.title)

    p.setFont("Helvetica", 16)
    p.drawCentredString(width/2.0, height-380, f"With a score of {attempt.percentage}% on {attempt.submitted_at.strftime('%B %d, %Y')}")

    p.setFont("Helvetica-Oblique", 14)
    p.drawCentredString(width/2.0, height-450, "ExamFlow Platform")
    
    p.showPage()
    p.save()
    buffer.seek(0)

    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{exam.slug}-certificate.pdf"',
    })
