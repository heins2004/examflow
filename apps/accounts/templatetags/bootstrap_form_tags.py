from django import template
from django.forms.boundfield import BoundField
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.safestring import mark_safe

register = template.Library()


def _render_errors(errors):
    if not errors:
        return ""
    return format_html(
        '<div class="invalid-feedback d-block">{}</div>',
        format_html_join("", "{}", ((conditional_escape(error),) for error in errors)),
    )


def _render_help_text(help_text):
    if not help_text:
        return ""
    return format_html('<div class="form-text">{}</div>', help_text)


def _render_bound_field(field):
    widget_name = field.field.widget.__class__.__name__.lower()
    if "checkbox" in widget_name:
        return format_html(
            '<div class="form-check mb-3">{} <label class="form-check-label" for="{}">{}</label>{}{}</div>',
            field,
            field.id_for_label,
            field.label,
            _render_help_text(field.help_text),
            _render_errors(field.errors),
        )

    return format_html(
        '<div class="mb-3"><label class="form-label" for="{}">{}</label>{}{}{}</div>',
        field.id_for_label,
        field.label,
        field,
        _render_help_text(field.help_text),
        _render_errors(field.errors),
    )


@register.filter(name="crispy")
def crispy(value):
    if isinstance(value, BoundField):
        return _render_bound_field(value)

    if hasattr(value, "visible_fields"):
        hidden_fields = "".join(str(field) for field in value.hidden_fields())
        non_field_errors = value.non_field_errors()
        visible_fields = "".join(str(_render_bound_field(field)) for field in value.visible_fields())
        rendered_errors = ""
        if non_field_errors:
            rendered_errors = str(
                format_html(
                    '<div class="alert alert-danger">{}</div>',
                    format_html_join("", "{}", ((conditional_escape(error),) for error in non_field_errors)),
                )
            )
        return mark_safe(hidden_fields + rendered_errors + visible_fields)

    return value
