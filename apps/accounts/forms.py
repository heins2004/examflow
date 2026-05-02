from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing_class = widget.attrs.get('class', '')
            widget_name = widget.__class__.__name__.lower()

            if 'checkbox' in widget_name or 'radio' in widget_name:
                css_class = 'form-check-input'
            elif 'select' in widget_name:
                css_class = 'form-select'
            else:
                css_class = 'form-control'

            widget.attrs['class'] = f'{existing_class} {css_class}'.strip()


class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    EXAMINER_FEE = 499.00

    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, 'Student'),
            (User.Role.EXAMINER, 'Examiner'),
        ],
        initial=User.Role.STUDENT,
    )
    examiner_demo_payment = forms.BooleanField(
        required=False,
        label='Demo examiner payment confirmed',
        help_text='Required only if you want to register as an examiner.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'examiner_demo_payment')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        paid = cleaned_data.get('examiner_demo_payment')
        if role == User.Role.EXAMINER and not paid:
            self.add_error('examiner_demo_payment', 'Examiner registration requires the demo payment confirmation.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == User.Role.EXAMINER:
            user.examiner_payment_status = User.PaymentStatus.PAID
            user.examiner_payment_amount = self.EXAMINER_FEE
            user.examiner_payment_reference = f"DEMO-PAY-{user.username.upper()}"
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Remember Me")


class UserProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'gender', 'date_of_birth', 'bio', 'profile_picture')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
