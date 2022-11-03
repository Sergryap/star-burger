from django import template
from environs import Env
from calcdistances.models import PlaceCoord
from django.utils.html import format_html

register = template.Library()


@register.filter
def block_available_restaurants(value, arg):
    env = Env()
    env.read_env()
    apikey = env('APIKEY')
    order = value[arg]
    return create_info_restaurants_to_order(order, apikey)


def create_info_restaurants_to_order(order, apikey):
    if order['restaurants'][0].get('prepare'):
        dist = PlaceCoord.objects.calculate_dist_places(
            order['address'],
            order['restaurants'][0]['address'],
            apikey
        )
        return format_html(
            f'''
                Заказ готовится рестораном:<br>&#10004{order['restaurants'][0]['name']} - {dist} км
            '''
        )

    text_html = ''.join(
        sorted(
            [
                f'''&#10004{t['name']} - {
                PlaceCoord.objects.calculate_dist_places(
                    order['address'],
                    t['address'],
                    apikey
                )
                } км<br>'''
                for t in order['restaurants']
            ],
            key=lambda t: float(t.split()[-2])
        )
    )

    return format_html(
        f'''
        <details>
            <summary>Может быть приготовлен &#9660</summary>
            {text_html}
        </details>
        '''
    )

