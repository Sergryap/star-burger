import re
import requests
import xxhash
from calcdistances.models import PlaceCoord
from django.utils.html import format_html
from math import sin, cos, radians, acos
from foodcartapp.models import Order, Restaurant
from django.conf import settings


def create_all_blocks_available_restaurants(restaurants_available):
    all_blocks_available_restaurants = {}
    for order_id, order in restaurants_available.items():
        try:
            all_blocks_available_restaurants.update(
                {order_id: create_block_available_restaurants(order)}
            )
        except requests.exceptions.HTTPError:
            all_blocks_available_restaurants.update(
                {order_id: 'Нет данных'}
            )
    return all_blocks_available_restaurants


def create_block_available_restaurants(order):
    if order['restaurants'][0].get('prepare'):
        dist = calculate_dist_places(
            order=order,
            restaurant=order['restaurants'][0],
            apikey=settings.GEO_TOKEN
        )

        return format_html(
            f'''
                Заказ готовится рестораном:<br>&#10004{order['restaurants'][0]['name']} - {dist} км
            '''
        )

    text_html = ''.join(
        sorted(
            [
                f'''&#10004{restaurant['name']} - {
                calculate_dist_places(
                    order=order,
                    restaurant=restaurant,
                    apikey=settings.GEO_TOKEN
                )
                }<br>'''
                for restaurant in order['restaurants']
            ], key=lambda x: re.search(r'(\d+\.?\d*)\s*км', x).group(1) if re.search(r'(\d+\.?\d*)\s*км', x) else x
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


def calculate_dist_places(order, restaurant, apikey):
    hash_current_order = xxhash.xxh32(order['address'].encode()).intdigest()
    hash_current_restaurant = xxhash.xxh32(restaurant['address'].encode()).intdigest() if restaurant['address'] else 0

    # Проверяем было ли изменение адреса ордера или добавление нового:
    if hash_current_order == order['hash']:
        order_lng = order['coordinates']['lng']
        order_lat = order['coordinates']['lat']
    else:
        place_order, created = PlaceCoord.objects.get_or_create(
            hash=hash_current_order,
            defaults=fetch_coordinates(apikey, order['address'])
        )
        # Назначаем place_id для order:
        if hash_current_order != order['hash']:
            order_current = Order.objects.get(pk=order['id'])
            order_current.place_id = place_order.id
            order_current.save()
            order['hash'] = hash_current_order
        order_lng = place_order.lng
        order_lat = place_order.lat

    # Проверяем было ли изменение адреса ресторана или добавление нового:
    if hash_current_restaurant == restaurant['hash']:
        restaurant_lng = restaurant['coordinates']['lng']
        restaurant_lat = restaurant['coordinates']['lat']
    else:
        place_restaurant, created = PlaceCoord.objects.get_or_create(
            hash=hash_current_restaurant,
            defaults=fetch_coordinates(apikey, restaurant['address'])
        )
        # Назначаем place_id для restaurant
        if hash_current_restaurant != restaurant['hash']:
            restaurant_current = Restaurant.objects.get(pk=restaurant['restaurant_id'])
            restaurant_current.place_id = place_restaurant.id
            restaurant_current.save()
            restaurant['hash'] = hash_current_restaurant
        restaurant_lng = place_restaurant.lng
        restaurant_lat = place_restaurant.lat

    lng1, lat1, lng2, lat2 = [
            radians(i) for i in (order_lng, order_lat, restaurant_lng, restaurant_lat)
        ]
    dist_rad = acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng1 - lng2))
    dist_km = round(settings.EARTH_RADIUS * dist_rad, 2)

    return f'{dist_km} км'
