from django import template

register = template.Library()


@register.filter
def get_available_restaurants(value, arg):
    return value[arg]
