from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def get_restaurants_order_available(value, arg):
    if value.get(arg)[0].get('prepare'):
        return format_html(
            f'''
                Заказ готовится рестораном:<br>&#10004{value.get(arg)[0].get('name')}
            '''
        )

    text_html = ''.join(
        [f'&#10004{t["name"]}<br>' for t in value.get(arg)]
    )
    return format_html(
        f'''
        <details>
            <summary>Может быть приготовлен &#9660</summary>
            {text_html}
        </details>
        '''
    )
