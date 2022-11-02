from math import sin, cos, radians, acos
from django.utils.html import format_html
from calcdistances.models import PlaceCoord


def calculate_dist_places(place1, place2, apikey):
    place1 = PlaceCoord.objects.get_or_create_place(apikey, place1)
    place2 = PlaceCoord.objects.get_or_create_place(apikey, place2)

    try:
        lng1, lat1 = [radians(i) for i in (place1.lng, place1.lat)]
        lng2, lat2 = [radians(i) for i in (place2.lng, place2.lat)]
        dist_rad = acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng1 - lng2))
        dist_km = round(6371 * dist_rad, 2)
        return f'{str(dist_km)} км'
    except Exception:
        return "Ошибка определения координат"


def create_info_restaurants_to_order(order, apikey):

    if order['restaurants'][0].get('prepare'):
        dist = calculate_dist_places(
            order['address'],
            order['restaurants'][0]['address'],
            apikey
        )
        return format_html(
            f'''
                Заказ готовится рестораном:<br>&#10004{order['restaurants'][0]['name']} - {dist}
            '''
        )

    text_html = ''.join(
        sorted(
            [
                f'''&#10004{t['name']} - {
                calculate_dist_places(order['address'], t['address'], apikey)
                }<br>'''
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
