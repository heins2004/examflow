import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from .models import Exam, Category, ExamAttempt, Question, Option, UserAnswer
from django.db.models import Count

def exam_list(request):
    exams = Exam.objects.filter(is_active=True).order_by('-created_at')
    categories = Category.objects.all()
    
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

def exam_detail(request, slug):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    user_attempts = 0
    completed_attempts = 0
    in_progress_attempt = None
    if request.user.is_authenticated:
        attempt_qs = ExamAttempt.objects.filter(user=request.user, exam=exam)
        user_attempts = attempt_qs.count()
        completed_attempts = attempt_qs.exclude(status='IN_PROGRESS').count()
        in_progress_attempt = attempt_qs.filter(status='IN_PROGRESS').first()
        
    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'user_attempts': user_attempts,
        'completed_attempts': completed_attempts,
        'in_progress_attempt': in_progress_attempt,
        'can_attempt': completed_attempts < exam.max_attempts if exam.max_attempts > 0 else True,
        'has_questions': exam.questions.exists(),
    })

@login_required
def exam_start(request, slug):
    exam = get_object_or_404(Exam, slug=slug, is_active=True)
    in_progress = ExamAttempt.objects.filter(user=request.user, exam=exam, status='IN_PROGRESS').first()
    if in_progress:
        return redirect('exam_attempt', slug=slug, id=in_progress.id)

    if not exam.questions.exists():
        messages.error(request, "This exam has no questions yet.")
        return redirect('exam_detail', slug=slug)

    completed_attempts = ExamAttempt.objects.filter(user=request.user, exam=exam).exclude(status='IN_PROGRESS').count()
    if exam.max_attempts > 0 and completed_attempts >= exam.max_attempts:
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
                
                if question.question_type == 'FILL_BLANK':
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
        if ans.question.question_type == 'FILL_BLANK':
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
        
        if q.question_type == 'FILL_BLANK':
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
    
    if not attempt.is_passed or attempt.status != 'SUBMITTED':
        messages.error(request, 'You need to pass the exam to download the certificate.')
        return redirect('exam_result', slug=slug, id=id)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter
    import io
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    p.setFillColorRGB(0.1, 0.12, 0.36)
    p.rect(0, 0, width, height, stroke=0, fill=1)
    
    p.setFillColorRGB(1, 1, 1)
    p.rect(20, 20, width-40, height-40, stroke=1, fill=1)

    p.setFillColorRGB(0.1, 0.12, 0.36)
    p.setFont("Helvetica-Bold", 40)
    p.drawCentredString(width/2.0, height-100, "CERTIFICATE OF COMPLETION")

    p.setFont("Helvetica", 20)
    p.drawCentredString(width/2.0, height-160, "This is to certify that")

    p.setFont("Helvetica-Bold", 30)
    p.setFillColorRGB(0.42, 0.38, 1)
    p.drawCentredString(width/2.0, height-210, attempt.user.get_full_name() or attempt.user.username)

    p.setFillColorRGB(0.1, 0.12, 0.36)
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
