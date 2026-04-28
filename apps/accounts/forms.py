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

            if 'checkbox' in widget_name:
                css_class = 'form-check-input'
            elif 'select' in widget_name:
                css_class = 'form-select'
            else:
                css_class = 'form-control'

            widget.attrs['class'] = f'{existing_class} {css_class}'.strip()


class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, 'Student'),
            (User.Role.EXAMINER, 'Examiner'),
        ],
        initial=User.Role.STUDENT,
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role')


class CustomAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Remember Me")


class UserProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'gender', 'date_of_birth', 'bio', 'profile_picture')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
