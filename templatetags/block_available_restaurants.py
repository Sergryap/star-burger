from django import template
from environs import Env
from calcdistances.views import create_info_restaurants_to_order

register = template.Library()


@register.filter
def block_available_restaurants(value, arg):
    env = Env()
    env.read_env()
    apikey = env('APIKEY')
    order = value[arg]
    return create_info_restaurants_to_order(order, apikey)
