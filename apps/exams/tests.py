from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.exams.models import Category, Exam


class ExamPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='student', password='student123')
        cls.category, _ = Category.objects.get_or_create(
            name='Mathematics',
            defaults={'slug': 'mathematics'},
        )
        cls.exam = Exam.objects.create(
            title='Algebra Basics',
            slug='algebra-basics',
            description='Basic algebra practice exam.',
            category=cls.category,
            exam_type='PRACTICE',
            duration_minutes=30,
            total_marks=100,
            pass_marks=40,
            is_released=True,
            created_by=cls.user,
        )

    def test_exam_list_page_loads(self):
        response = self.client.get(reverse('exam_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.exam.title)

    def test_exam_detail_page_loads(self):
        response = self.client.get(reverse('exam_detail', kwargs={'slug': self.exam.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.exam.title)
