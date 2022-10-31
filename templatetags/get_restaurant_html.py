from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def get_restaurant_html(value, arg):
    text = [v['name'] for v in value.get(arg)]
    text_html = f"<ul>{''.join([('<li>' + '<i>' + t + '</i>' + '</li>') for t in text])}</ul>"
    return format_html(
        f'''
        <details>
            <summary>Может быть приготовлен ресторанами<b> >> </b></summary>
            {text_html}
        </details>
        '''
    )
