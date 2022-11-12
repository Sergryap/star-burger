import re
import requests
import xxhash
from django import template
from django.db.models import Q
from environs import Env
from calcdistances.models import PlaceCoord
from django.utils.html import format_html
from math import sin, cos, radians, acos
from foodcartapp.models import Order, Restaurant

register = template.Library()


@register.filter
def block_available_restaurants(value, arg):
    env = Env()
    env.read_env()
    apikey = env('APIKEY')
    order = value[arg]
    return create_info_restaurants_to_order(order, apikey, order_id=arg)


def create_info_restaurants_to_order(order, apikey, order_id):
    if order['restaurants'][0].get('prepare'):
        dist = calculate_dist_places(
            order_id=order_id,
            order_coord=order['coordinates'],
            restaurant_id=order['restaurants'][0]['restaurant'],
            restaurant_coord=order['restaurants'][0]['coordinates'],
            order_address=order['address'],
            restaurant_address=order['restaurants'][0]['address'],
            apikey=apikey
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
                calculate_dist_places(
                    order_id=order_id,
                    order_coord=order['coordinates'],
                    restaurant_id=t['restaurant'],
                    restaurant_coord=t['coordinates'],
                    order_address=order['address'],
                    restaurant_address=t['address'],
                    apikey=apikey
                )
                } км<br>'''
                for t in order['restaurants']
            ], key=lambda t: re.search(r'(\d+\.?\d*)\s*км<', t).group(1)
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


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lng, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

    return {'lng': float(lng), 'lat': float(lat), 'address': address}


def get_or_create_place(object_id, apikey, address, existing_place=None, model_order=True):
    """
    Возвращает экземпляр класса PlaceOrder.
    Если он не существует в базе, то он создается и возвращается.
    Если существует и равен existing_place, то возвращется existing_place
    """
    address_hash = xxhash.xxh32(address.encode()).intdigest()
    if existing_place and existing_place.hash == address_hash:
        return existing_place
    else:
        place = PlaceCoord.objects.create(
            **{'hash': address_hash, **fetch_coordinates(apikey, address)}
        )
        if model_order:
            order = Order.objects.get(pk=object_id)
            place.orders.add(order)
        else:
            restaurant = Restaurant.objects.get(pk=object_id)
            place.restaurants.add(restaurant)

        return place


def calculate_dist_places(
    order_id,
    order_coord,
    restaurant_id,
    restaurant_coord,
    order_address,
    restaurant_address,
    apikey
):
    if order_coord['lng'] and restaurant_coord['lng']:
        lng1, lat1, lng2, lat2 = [
            radians(i) for i in (
                order_coord['lng'], order_coord['lat'],
                restaurant_coord['lng'], restaurant_coord['lat']
            )
        ]
    else:
        places = list(
            PlaceCoord.objects
            .defer('request_at')
            .filter(
                Q(hash=xxhash.xxh32(order_address.encode()).intdigest()) |
                Q(hash=xxhash.xxh32(restaurant_address.encode()).intdigest())
            )
        )
        if len(places) == 2:
            place1, place2 = places
        else:
            existing_place = places[0] if len(places) == 1 else None
            try:
                place1 = get_or_create_place(order_id, apikey, order_address, existing_place)
                place2 = get_or_create_place(restaurant_id, apikey, restaurant_address, existing_place, model_order=False)
            except requests.exceptions.RequestException:
                return "Ошибка определения координат"
        lng1, lat1, lng2, lat2 = [
                radians(i) for i in (place1.lng, place1.lat, place2.lng, place2.lat)
            ]
    dist_rad = acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng1 - lng2))
    dist_km = round(6371 * dist_rad, 2)
    return dist_km
