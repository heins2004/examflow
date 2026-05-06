from django.db import migrations
from django.utils.text import slugify


DEFAULT_CATEGORIES = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English",
    "History",
    "Geography",
    "Computer Science",
    "Programming",
    "Data Structures",
    "Algorithms",
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Cyber Security",
    "Cloud Computing",
    "Networking",
    "Database Management",
    "Web Development",
    "Mobile Development",
    "Software Testing",
    "DevOps",
    "Aptitude",
    "Logical Reasoning",
    "Quantitative Aptitude",
    "Verbal Ability",
    "General Knowledge",
    "Economics",
    "Accounting",
    "Business Studies",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("exams", "Category")

    for name in DEFAULT_CATEGORIES:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 2
        while Category.objects.exclude(name=name).filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        Category.objects.get_or_create(
            name=name,
            defaults={
                "slug": slug,
                "description": f"Default ExamFlow category for {name}.",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0005_alter_exam_category"),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
