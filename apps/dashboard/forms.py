from django import forms
from django.utils.text import slugify

from apps.accounts.forms import BootstrapFormMixin
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import User
from apps.exams.models import Category, Exam, Option, Question
from .models import CategoryRequest


class ExamForm(BootstrapFormMixin, forms.ModelForm):
    slug = forms.SlugField(required=False, help_text="Leave blank to generate automatically.")
    pass_key = forms.CharField(required=False, help_text="Optional student pass key shared by the examiner.")

    class Meta:
        model = Exam
        exclude = ("created_by", "access_code", "exam_code")
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "No category"

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        title = (self.cleaned_data.get("title") or "").strip()
        slug = slug or slugify(title)
        if not slug:
            raise forms.ValidationError("Enter a title so a slug can be generated.")

        queryset = Exam.objects.filter(slug=slug)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("An exam with this slug already exists.")
        return slug



    def clean(self):
        cleaned_data = super().clean()
        duration_minutes = cleaned_data.get("duration_minutes")
        is_unlimited_time = cleaned_data.get("is_unlimited_time")
        pass_key = (cleaned_data.get("pass_key") or "").strip().upper()
        exam_type = cleaned_data.get("exam_type")
        certificate_template_upload = cleaned_data.get("certificate_template_upload")

        if not is_unlimited_time and not duration_minutes:
            self.add_error("duration_minutes", "Enter a duration or enable unlimited time.")

        if is_unlimited_time:
            cleaned_data["duration_minutes"] = None

        if exam_type != "CERTIFICATION" and certificate_template_upload:
            self.add_error("certificate_template_upload", "Certificate templates are only used for certification exams.")

        cleaned_data["pass_key"] = pass_key
        return cleaned_data


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    slug = forms.SlugField(required=False, help_text="Leave blank to generate automatically.")

    class Meta:
        model = Category
        fields = "__all__"

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        name = (self.cleaned_data.get("name") or "").strip()
        slug = slug or slugify(name)
        if not slug:
            raise forms.ValidationError("Enter a category name so a slug can be generated.")

        queryset = Category.objects.filter(slug=slug)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("A category with this slug already exists.")
        return slug


class QuestionForm(BootstrapFormMixin, forms.ModelForm):
    OPTION_CHOICES = [
        ("1", "Option 1"),
        ("2", "Option 2"),
        ("3", "Option 3"),
        ("4", "Option 4"),
    ]
    TRUE_FALSE_CHOICES = [
        ("True", "True"),
        ("False", "False"),
    ]

    option_1 = forms.CharField(required=False, label="Option 1")
    option_2 = forms.CharField(required=False, label="Option 2")
    option_3 = forms.CharField(required=False, label="Option 3")
    option_4 = forms.CharField(required=False, label="Option 4")
    correct_option = forms.ChoiceField(
        required=False,
        choices=OPTION_CHOICES,
        widget=forms.RadioSelect,
        label="Correct option",
    )
    true_false_answer = forms.ChoiceField(
        required=False,
        choices=TRUE_FALSE_CHOICES,
        widget=forms.RadioSelect,
        label="Correct answer",
    )
    fill_blank_answer = forms.CharField(
        required=False,
        label="Correct answer",
        help_text="Used for fill in the blank questions.",
    )
    short_answer = forms.CharField(
        required=False,
        label="Expected answer",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Used for short answer questions.",
    )

    class Meta:
        model = Question
        fields = [
            "exam",
            "question_text",
            "question_type",
            "image",
            "marks",
            "negative_marks",
            "explanation",
            "order",
        ]
        widgets = {
            "question_type": forms.RadioSelect,
        }

    def __init__(self, *args, exam_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        if exam_queryset is not None:
            self.fields["exam"].queryset = exam_queryset

        allowed_question_types = [
            ("MCQ", "MCQ"),
            ("TRUE_FALSE", "True or False"),
            ("FILL_BLANK", "Fill in the Blanks"),
            ("SHORT_ANSWER", "Short Answer"),
        ]
        if self.instance.pk and self.instance.question_type == "IMAGE_BASED":
            allowed_question_types.append(("IMAGE_BASED", "Image Based"))
        self.fields["question_type"].choices = allowed_question_types

        if not self.instance.pk:
            self.fields["question_type"].initial = None

        if self.instance.pk:
            options = list(self.instance.options.all())
            if self.instance.question_type in {"MCQ", "IMAGE_BASED"}:
                for index, option in enumerate(options[:4], start=1):
                    self.fields[f"option_{index}"].initial = option.option_text
                    if option.is_correct:
                        self.fields["correct_option"].initial = str(index)
            elif self.instance.question_type == "TRUE_FALSE":
                correct = next((option.option_text for option in options if option.is_correct), "")
                self.fields["true_false_answer"].initial = correct
            elif self.instance.question_type == "FILL_BLANK":
                correct = next((option.option_text for option in options if option.is_correct), "")
                self.fields["fill_blank_answer"].initial = correct
            elif self.instance.question_type == "SHORT_ANSWER":
                correct = next((option.option_text for option in options if option.is_correct), "")
                self.fields["short_answer"].initial = correct

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get("question_type")

        if question_type in {"MCQ", "IMAGE_BASED"}:
            options = [
                cleaned_data.get("option_1", "").strip(),
                cleaned_data.get("option_2", "").strip(),
                cleaned_data.get("option_3", "").strip(),
                cleaned_data.get("option_4", "").strip(),
            ]
            if len([option for option in options if option]) < 2:
                raise forms.ValidationError("Add at least two options for this question type.")

            correct_option = cleaned_data.get("correct_option")
            if not correct_option:
                raise forms.ValidationError("Select the correct option.")

            if not options[int(correct_option) - 1]:
                raise forms.ValidationError("The selected correct option cannot be empty.")

        elif question_type == "TRUE_FALSE":
            if not cleaned_data.get("true_false_answer"):
                raise forms.ValidationError("Select whether the correct answer is True or False.")

        elif question_type == "FILL_BLANK":
            answer = cleaned_data.get("fill_blank_answer", "").strip()
            if not answer:
                raise forms.ValidationError("Enter the correct answer for this fill in the blank question.")
            cleaned_data["fill_blank_answer"] = answer
        elif question_type == "SHORT_ANSWER":
            answer = cleaned_data.get("short_answer", "").strip()
            if not answer:
                raise forms.ValidationError("Enter the expected answer for this short answer question.")
            cleaned_data["short_answer"] = answer

        return cleaned_data

    def save(self, commit=True):
        question = super().save(commit=commit)

        if commit:
            question.options.all().delete()
            self._save_options(question)

        return question

    def _save_options(self, question):
        question_type = self.cleaned_data["question_type"]

        if question_type in {"MCQ", "IMAGE_BASED"}:
            correct_option = self.cleaned_data["correct_option"]
            for index in range(1, 5):
                option_text = self.cleaned_data.get(f"option_{index}", "").strip()
                if option_text:
                    Option.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=str(index) == correct_option,
                    )
            return

        if question_type == "TRUE_FALSE":
            answer = self.cleaned_data["true_false_answer"]
            Option.objects.create(question=question, option_text="True", is_correct=answer == "True")
            Option.objects.create(question=question, option_text="False", is_correct=answer == "False")
            return

        if question_type == "FILL_BLANK":
            Option.objects.create(
                question=question,
                option_text=self.cleaned_data["fill_blank_answer"],
                is_correct=True,
            )
            return

        if question_type == "SHORT_ANSWER":
            Option.objects.create(
                question=question,
                option_text=self.cleaned_data["short_answer"],
                is_correct=True,
            )


class DashboardUserCreateForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "password1", "password2")


class DashboardUserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "is_active")


class CategoryRequestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CategoryRequest
        fields = ("name", "description")
