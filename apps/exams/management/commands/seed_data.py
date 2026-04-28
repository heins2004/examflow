from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.exams.models import Category, Exam, Question, Option
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the database with sample categories, exams, questions, and an admin user'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        # Create Admin
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS("Created admin user (admin/admin)"))

        # Create Student
        if not User.objects.filter(username='student').exists():
            User.objects.create_user('student', 'student@example.com', 'student', role='STUDENT')
            self.stdout.write(self.style.SUCCESS("Created student user (student/student)"))

        # Create Category
        cat, created = Category.objects.get_or_create(
            name='Computer Science',
            slug='computer-science',
            defaults={'description': 'CS, Programming, and Tech.', 'icon': '💻'}
        )

        # Create Exam
        exam, created = Exam.objects.get_or_create(
            title='Python Fundamentals',
            slug='python-fundamentals',
            defaults={
                'description': 'Test your basic Python skills.',
                'category': cat,
                'exam_type': 'PRACTICE',
                'duration_minutes': 30,
                'total_marks': 5,
                'pass_marks': 3,
                'instructions': 'Answer all questions carefully.',
                'max_attempts': 3
            }
        )

        if created:
            # Create MCQ Question
            q1 = Question.objects.create(exam=exam, question_text="What is the output of print(2**3)?", question_type='MCQ', marks=1, order=1)
            Option.objects.create(question=q1, option_text="6", is_correct=False)
            Option.objects.create(question=q1, option_text="8", is_correct=True)
            Option.objects.create(question=q1, option_text="9", is_correct=False)

            # Create True/False
            q2 = Question.objects.create(exam=exam, question_text="Python is statically typed.", question_type='TRUE_FALSE', marks=1, order=2, explanation="Python is dynamically typed.")
            Option.objects.create(question=q2, option_text="True", is_correct=False)
            Option.objects.create(question=q2, option_text="False", is_correct=True)

            # Create Fill in Blank
            q3 = Question.objects.create(exam=exam, question_text="The keyword used to define a function is ____.", question_type='FILL_BLANK', marks=1, order=3)
            Option.objects.create(question=q3, option_text="def", is_correct=True)

            self.stdout.write(self.style.SUCCESS("Created Sample Exam with Questions."))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
