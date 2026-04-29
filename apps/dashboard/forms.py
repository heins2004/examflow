from django import forms
from django.utils.text import slugify

from apps.accounts.forms import BootstrapFormMixin
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import User
from apps.exams.models import Category, Exam, Option, Question


class ExamForm(BootstrapFormMixin, forms.ModelForm):
    slug = forms.SlugField(required=False, help_text="Leave blank to generate automatically.")
    exam_code = forms.CharField(required=False, help_text="Leave blank to generate automatically.")
    access_code = forms.CharField(required=False, help_text="Required only for private exams.")
    pass_key = forms.CharField(required=False, help_text="Optional student pass key shared by the examiner.")

    class Meta:
        model = Exam
        exclude = ("created_by",)
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

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

    def clean_exam_code(self):
        exam_code = (self.cleaned_data.get("exam_code") or "").strip().upper()
        if not exam_code:
            return exam_code

        queryset = Exam.objects.filter(exam_code=exam_code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("An exam with this exam code already exists.")
        return exam_code

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get("visibility")
        access_code = (cleaned_data.get("access_code") or "").strip().upper()
        pass_key = (cleaned_data.get("pass_key") or "").strip().upper()

        if visibility == "PRIVATE" and not access_code:
            self.add_error("access_code", "Private exams require an access code.")

        cleaned_data["access_code"] = access_code
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

    def __init__(self, *args, exam_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        if exam_queryset is not None:
            self.fields["exam"].queryset = exam_queryset

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


class DashboardUserCreateForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "password1", "password2")


class DashboardUserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "is_active")
