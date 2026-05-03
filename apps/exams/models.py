from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True) # Emoji or SVG class
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Exam(models.Model):
    VISIBILITY_CHOICES = (
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
    )
    EXAM_TYPE_CHOICES = (
        ('PRACTICE', 'Practice'),
        ('MOCK', 'Mock'),
        ('CERTIFICATION', 'Certification'),
        ('COMPETITIVE', 'Competitive'),
    )
    CERTIFICATE_TEMPLATE_CHOICES = tuple(
        (f'TEMPLATE_{index}', f'Template {index}')
        for index in range(1, 11)
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='exams')
    exam_type = models.CharField(max_length=50, choices=EXAM_TYPE_CHOICES)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_unlimited_time = models.BooleanField(default=False)
    total_marks = models.PositiveIntegerField()
    pass_marks = models.PositiveIntegerField()
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    allow_review = models.BooleanField(default=True)
    show_result_immediately = models.BooleanField(default=True)
    max_attempts = models.PositiveIntegerField(default=1)
    one_attempt_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_released = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC')
    exam_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    access_code = models.CharField(max_length=20, blank=True, null=True)
    pass_key = models.CharField(max_length=20, blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to='exam_thumbnails/', null=True, blank=True)
    instructions = models.TextField(blank=True, null=True)
    certificate_template = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TEMPLATE_CHOICES,
        default='TEMPLATE_1',
    )
    certificate_template_upload = models.ImageField(
        upload_to='certificate_templates/',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_exams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.exam_code:
            self.exam_code = self._generate_unique_code('EXM')
        self.exam_code = (self.exam_code or '').upper()
        self.access_code = self.exam_code
        if self.is_unlimited_time:
            self.duration_minutes = None
        super().save(*args, **kwargs)

    def _generate_unique_code(self, prefix):
        while True:
            code = f"{prefix}-{get_random_string(6).upper()}"
            if not Exam.objects.filter(exam_code=code).exists():
                return code

    @property
    def requires_access_code(self):
        return self.visibility == 'PRIVATE' and bool(self.access_code)

    @property
    def requires_pass_key(self):
        return bool(self.pass_key)

    @property
    def duration_label(self):
        if self.is_unlimited_time or not self.duration_minutes:
            return 'Unlimited'
        return f'{self.duration_minutes}m'

    @property
    def is_certification(self):
        return self.exam_type == 'CERTIFICATION'

class Question(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('MCQ', 'Multiple Choice Question'),
        ('TRUE_FALSE', 'True/False'),
        ('FILL_BLANK', 'Fill in the Blank'),
        ('SHORT_ANSWER', 'Short Answer'),
        ('IMAGE_BASED', 'Image Based'),
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    image = models.ImageField(upload_to='question_images/', null=True, blank=True)
    marks = models.PositiveIntegerField(default=1)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    explanation = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question_text[:50]

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    option_image = models.ImageField(upload_to='option_images/', null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.option_text[:50]

class ExamAttempt(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('TIMED_OUT', 'Timed Out'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='IN_PROGRESS')
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_passed = models.BooleanField(default=False)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    attempt_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.started_at}"


class ExamAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_accesses')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='accesses')
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'exam')

    def __str__(self):
        return f"{self.user.username} -> {self.exam.exam_code}"

class UserAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.CharField(max_length=500, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Ans: {self.attempt.user.username} - {self.question.id}"
