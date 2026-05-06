import json
import csv
import hashlib
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


def build_certificate_id(attempt):
    student_label = attempt.user.get_full_name() or attempt.user.username
    source = f"{attempt.exam.slug}|{student_label}|{attempt.id}"
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8].upper()
    year = (attempt.submitted_at or timezone.now()).strftime("%Y")
    return f"EF-{year}-{digest}"

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
    from reportlab.lib.colors import Color
    import io

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    navy = Color(0.10, 0.10, 0.18)
    gold = Color(0.79, 0.66, 0.30)
    soft_bg = Color(0.98, 0.98, 0.97)
    border = Color(0.84, 0.82, 0.78)
    muted = Color(0.42, 0.42, 0.42)
    pale_panel = Color(0.94, 0.93, 0.90)
    verify_bg = Color(0.90, 0.96, 0.92)
    verify_fg = Color(0.18, 0.42, 0.31)

    certificate_id = build_certificate_id(attempt)
    student_name = attempt.user.get_full_name() or attempt.user.username
    issued_by = exam.created_by.get_full_name() if exam.created_by and exam.created_by.get_full_name() else (exam.created_by.username if exam.created_by else "ExamFlow")
    completion_date = (attempt.submitted_at or timezone.now()).strftime("%d %B %Y")
    duration_label = exam.duration_label

    p.setFillColor(soft_bg)
    p.rect(0, 0, width, height, stroke=0, fill=1)
    p.setFillColor(navy)
    p.rect(0, 0, 8, height, stroke=0, fill=1)
    p.setFillColor(gold)
    p.rect(8, 0, 3, height, stroke=0, fill=1)

    p.setStrokeColor(border)
    p.setLineWidth(1)
    p.rect(24, 20, width - 44, height - 40, stroke=1, fill=0)
    p.setStrokeColor(navy)
    p.rect(28, 24, width - 52, height - 48, stroke=1, fill=0)

    for x in range(60, int(width - 40), 24):
        for y in range(50, int(height - 40), 24):
            p.setFillColor(Color(0.93, 0.94, 0.96))
            p.circle(x, y, 0.6, stroke=0, fill=1)

    p.setFillColor(navy)
    p.roundRect(46, height - 65, 22, 22, 4, stroke=0, fill=1)
    p.setFillColor(gold)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(57, height - 50, "*")
    p.setFillColor(navy)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(78, height - 51, "Exam")
    p.setFillColor(gold)
    p.drawString(118, height - 51, "Flow")

    p.setFillColor(muted)
    p.setFont("Helvetica", 9)
    p.drawRightString(width - 48, height - 38, "CERTIFICATE NO.")
    p.setFillColor(navy)
    p.setFont("Helvetica-Bold", 10)
    p.drawRightString(width - 48, height - 52, certificate_id)

    p.setFillColor(gold)
    p.rect(42, height - 82, width - 84, 2, stroke=0, fill=1)

    left_x = 46
    right_x = width - 182
    divider_x = width - 205
    top_y = height - 110

    p.setFillColor(gold)
    p.setFont("Helvetica", 10)
    p.drawString(left_x, top_y, "CERTIFICATE OF ACHIEVEMENT")
    p.setFillColor(navy)
    p.setFont("Times-Bold", 28)
    p.drawString(left_x, top_y - 30, "Certificate of")
    p.drawString(left_x, top_y - 60, "Completion")

    p.setFillColor(muted)
    p.setFont("Helvetica", 10)
    p.drawString(left_x, top_y - 94, "PRESENTED TO")

    p.setFillColor(navy)
    p.setFont("Times-Bold", 24)
    p.drawString(left_x, top_y - 124, student_name[:45])
    p.setStrokeColor(gold)
    p.line(left_x, top_y - 132, width - 240, top_y - 132)

    p.setFillColor(muted)
    p.setFont("Helvetica", 11)
    text = p.beginText(left_x, top_y - 160)
    text.setLeading(15)
    text.textLines(
        "has successfully completed all requirements and demonstrated proficiency\n"
        "in the following examination administered through the ExamFlow platform."
    )
    p.drawText(text)

    panel_y = 124
    panel_h = 112
    p.setFillColor(pale_panel)
    p.setStrokeColor(border)
    p.roundRect(left_x, panel_y, width - 300, panel_h, 6, stroke=1, fill=1)

    p.setFillColor(gold)
    p.setFont("Helvetica", 9)
    p.drawString(left_x + 14, panel_y + panel_h - 18, "EXAMINATION TITLE")
    p.setFillColor(navy)
    p.setFont("Times-Bold", 16)
    p.drawString(left_x + 14, panel_y + panel_h - 38, exam.title[:55])

    p.setFillColor(navy)
    p.roundRect(width - 268, panel_y + panel_h - 28, 70, 18, 9, stroke=0, fill=1)
    p.setFillColor(gold)
    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(width - 233, panel_y + panel_h - 22, f"Score: {attempt.percentage:.0f}%")

    meta_y = panel_y + 36
    meta_width = (width - 340) / 3
    meta_values = [
        ("DATE OF COMPLETION", completion_date),
        ("DURATION", duration_label),
        ("ISSUED BY", issued_by[:28]),
    ]
    for index, (label, value) in enumerate(meta_values):
        current_x = left_x + 14 + (meta_width * index)
        p.setFillColor(muted)
        p.setFont("Helvetica", 8)
        p.drawString(current_x, meta_y + 24, label)
        p.setStrokeColor(gold)
        p.line(current_x, meta_y + 6, current_x + meta_width - 20, meta_y + 6)
        p.setFillColor(navy)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(current_x, meta_y + 10, value)

    p.setStrokeColor(border)
    p.line(divider_x, 60, divider_x, height - 110)

    seal_center_x = right_x + 60
    seal_center_y = height - 175
    p.setStrokeColor(gold)
    p.setLineWidth(2)
    p.circle(seal_center_x, seal_center_y, 38, stroke=1, fill=0)
    p.setLineWidth(1)
    p.circle(seal_center_x, seal_center_y, 30, stroke=1, fill=0)
    p.setFillColor(gold)
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(seal_center_x, seal_center_y + 5, "*")
    p.setFillColor(gold)
    p.setFont("Helvetica-Bold", 8)
    p.drawCentredString(seal_center_x, seal_center_y - 8, "ExamFlow")
    p.drawCentredString(seal_center_x, seal_center_y - 18, "Verified")

    def draw_signature_block(y, label, signer):
        p.setStrokeColor(navy)
        p.line(right_x, y, width - 48, y)
        p.setFillColor(navy)
        p.setFont("Helvetica-Oblique", 12)
        p.drawCentredString((right_x + width - 48) / 2, y + 8, signer[:28])
        p.setFillColor(muted)
        p.setFont("Helvetica", 8)
        p.drawCentredString((right_x + width - 48) / 2, y - 12, label)

    draw_signature_block(175, "Exam Provider", issued_by)
    draw_signature_block(115, "ExamFlow Director", "ExamFlow Team")

    p.setStrokeColor(border)
    p.line(42, 64, width - 42, 64)
    p.setFillColor(muted)
    p.setFont("Helvetica", 8)
    p.drawString(46, 49, "ISSUED BY")
    p.setFillColor(navy)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(98, 49, issued_by[:42])

    p.setFillColor(verify_bg)
    p.setStrokeColor(Color(0.58, 0.84, 0.70))
    p.roundRect(width - 118, 40, 72, 18, 9, stroke=1, fill=1)
    p.setFillColor(verify_fg)
    p.setFont("Helvetica-Bold", 8)
    p.drawCentredString(width - 82, 46, "VERIFIED")
    
    p.showPage()
    p.save()
    buffer.seek(0)

    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{certificate_id.lower()}-{exam.slug}-certificate.pdf"',
    })
