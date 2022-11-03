import requests
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from math import sin, cos, radians, acos


class PlaceCoordQuerySet(models.QuerySet):

    @staticmethod
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

        return {'lng': float(lng), 'lat': float(lat)}

    def get_or_create_place(self, apikey, address):
        return (
            PlaceCoord.objects
            .defer('request_time')
            .get_or_create(
                address=address,
                defaults=self.fetch_coordinates(apikey, address))
        )[0]

    def calculate_dist_places(self, address1, address2, apikey):
        place1 = self.get_or_create_place(apikey, address1)
        place2 = self.get_or_create_place(apikey, address2)

        try:
            lng1, lat1, lng2, lat2 = [
                radians(i) for i in (place1.lng, place1.lat, place2.lng, place2.lat)
            ]
            dist_rad = acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng1 - lng2))
            dist_km = round(6371 * dist_rad, 2)
            return dist_km
        except Exception:
            return "Ошибка определения координат"


class PlaceCoord(models.Model):
    address = models.CharField(
        max_length=255,
        verbose_name='адрес',
        unique=True,
        db_index=True
    )
    lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180)
        ]
    )
    lat = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        validators=[
            MinValueValidator(limit_value=-90),
            MaxValueValidator(limit_value=90)
        ]
    )
    request_time = models.DateTimeField(
        verbose_name='время запроса',
        default=timezone.now,
        db_index=True
    )

    objects = PlaceCoordQuerySet.as_manager()
