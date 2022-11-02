import requests
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


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
        place = (
            PlaceCoord.objects
            .get_or_create(
                address=address,
                defaults=self.fetch_coordinates(apikey, address))
        )[0]
        return place


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
