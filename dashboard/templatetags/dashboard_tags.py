from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        val = dictionary.get(key, "")
        if val is None:
            return ""
        s = str(val).strip()
        if s.lower() in ("nan", "nat", "none", "<nat>"):
            return ""
        return val
    return ""


@register.filter
def trim(value):
    if isinstance(value, str):
        return value.strip()
    return value
