from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        EXAMINER = 'EXAMINER', 'Examiner'
        ADMIN = 'ADMIN', 'Admin'

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    examiner_payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_REQUIRED,
    )
    examiner_payment_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    examiner_payment_reference = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_staff = True
        elif self.role in {self.Role.ADMIN, self.Role.EXAMINER}:
            self.is_staff = True
        else:
            self.is_staff = False

        if self.role == self.Role.EXAMINER:
            if self.examiner_payment_status == self.PaymentStatus.NOT_REQUIRED:
                self.examiner_payment_status = self.PaymentStatus.PENDING
        else:
            self.examiner_payment_status = self.PaymentStatus.NOT_REQUIRED
            self.examiner_payment_amount = 0
            self.examiner_payment_reference = None
        super().save(*args, **kwargs)

    @property
    def can_manage_paid_exams(self):
        return self.role in {self.Role.ADMIN, self.Role.EXAMINER} and (
            self.role == self.Role.ADMIN or self.examiner_payment_status == self.PaymentStatus.PAID
        )

    def __str__(self):
        return self.username
