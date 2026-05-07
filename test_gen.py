import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'examflow.settings')
django.setup()

from apps.exams.models import ExamAttempt
attempt = ExamAttempt.objects.last()

from apps.exams.views import exam_certificate
from django.test import RequestFactory

request = RequestFactory().get('/')
request.user = attempt.user if attempt else None

if attempt:
    try:
        response = exam_certificate(request, slug=attempt.exam.slug, id=attempt.id)
        print("Response status:", response.status_code)
        if response.status_code == 200:
            with open('test_cert.pdf', 'wb') as f:
                f.write(b''.join(response.streaming_content))
            print("Wrote to test_cert.pdf successfully.")
    except Exception as e:
        print("Error:", repr(e))
else:
    print("No attempts found.")
