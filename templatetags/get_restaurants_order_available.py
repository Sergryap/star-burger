from django import template
from django.utils.html import format_html

from test_api_yandex import calculate_dist_places

register = template.Library()


@register.filter
def get_restaurants_order_available(value, arg):
    order = value[arg]

    if order['restaurants'][0].get('prepare'):
        dist = calculate_dist_places(order['address'], order['restaurants'][0]['address'])
        return format_html(
            f'''
                Заказ готовится рестораном:<br>&#10004{order['restaurants'][0]['name']} - {dist}
            '''
        )

    text_html = ''.join(
        sorted(
            [
                f"&#10004{t['name']} - {calculate_dist_places(order['address'], t['address'])}<br>"
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
