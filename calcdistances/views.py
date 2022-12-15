import requests
import xxhash
from calcdistances.models import PlaceCoord
from foodcartapp.models import Order, Restaurant
from django.conf import settings


def update_all_order_place_ids(order_data):
    modified = []
    for order in order_data.values():
        try:
            for restaurant in order['restaurants']:
                modified.append(
                    update_order_place_id(
                        order=order,
                        restaurant=restaurant,
                        apikey=settings.GEO_TOKEN
                    )
                )
        except requests.exceptions.HTTPError:
            print('Ошибка получения данных')

    return any(modified)


def fetch_coordinates(apikey, address):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    response = requests.get(base_url, params={
        'geocode': address,
        'apikey': apikey,
        'format': 'json',
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lng, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

    return {'lng': float(lng), 'lat': float(lat), 'address': address}


def update_order_place_id(order, restaurant, apikey):
    hash_current_order = xxhash.xxh32(order['address'].encode()).intdigest()
    hash_current_restaurant = xxhash.xxh32(restaurant['address'].encode()).intdigest() if restaurant['address'] else 0
    modified = False
    # Проверяем было ли изменение адреса ордера или добавление нового:
    if hash_current_order != order['hash']:
        modified = True
        order_place, created = PlaceCoord.objects.get_or_create(
            hash=hash_current_order,
            defaults=fetch_coordinates(apikey, order['address'])
        )
        # Назначаем place_id для order:
        current_order = Order.objects.get(pk=order['pk'])
        current_order.place = order_place
        current_order.save()
        order['hash'] = hash_current_order

    # Проверяем было ли изменение адреса ресторана или добавление нового:
    if hash_current_restaurant != restaurant['hash']:
        modified = True
        restaurant_place, created = PlaceCoord.objects.get_or_create(
            hash=hash_current_restaurant,
            defaults=fetch_coordinates(apikey, restaurant['address'])
        )
        # Назначаем place_id для restaurant
        current_restaurant = Restaurant.objects.get(pk=restaurant['restaurant_id'])
        current_restaurant.place = restaurant_place
        current_restaurant.save()
        restaurant['hash'] = hash_current_restaurant

    return modified
