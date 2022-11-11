from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class PlaceCoord(models.Model):
    address = models.CharField(
        max_length=255,
        verbose_name='адрес',
        unique=True,
    )
    lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180)
        ],
        blank=True,
        null=True,
    )
    lat = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        validators=[
            MinValueValidator(limit_value=-90),
            MaxValueValidator(limit_value=90)
        ],
        blank=True,
        null=True,
    )
    request_at = models.DateTimeField(
        verbose_name='время запроса',
        default=timezone.now
    )
    hash = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        validators=[MaxValueValidator(limit_value=9999999999)]
    )

    class Meta:
        app_label = 'calcdistances'
