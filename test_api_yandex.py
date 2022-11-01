import requests
from math import sin, cos, radians, acos
from environs import Env


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
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def calculate_dist_places(place1, place2):
    env = Env()
    env.read_env()
    key = env('APIKEY')

    try:
        lng1, lat1 = [float(i) for i in fetch_coordinates(key, place1)]
        lng2, lat2 = [float(i) for i in fetch_coordinates(key, place2)]
        lt1, lt2, ln1, ln2 = [radians(i) for i in (lat1, lat2, lng1, lng2)]
        dist_rad = acos(sin(lt1) * sin(lt2) + cos(lt1) * cos(lt2) * cos(ln1 - ln2))
        dist_km = round(6371 * dist_rad, 2)
        return f'{str(dist_km)} км'
    except Exception:
        return "Ошибка определения координат"





if __name__ == '__main__':
    print(calculate_dist_places('Пермь', 'Сочи'))
