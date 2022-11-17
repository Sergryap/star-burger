from django.utils.translation import gettext_lazy as _
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum, F, OuterRef, Subquery, Prefetch, Count
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from calcdistances.models import PlaceCoord


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )
    place = models.ForeignKey(
        PlaceCoord,
        related_name='restaurants',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):

    def add_total_cost(self):
        order_cost = (
            OrderPosition.objects
            .values('order_id')
            .annotate(total=Sum(F('price') * F('quantity')))
            .filter(order=OuterRef('pk'))
        )
        return (
            self.defer(
                'restaurant_order',
                'registrated_at',
                'called_at',
                'delivered_at'
            ).annotate(total=Subquery(order_cost.values('total')))
        )

    def get_restaurants_available(self):
        restaurants_available = {}
        orders_restaurant = self.raw(
            '''
            SELECT
                fr.id, restaurant_id, fo3.order_id, fr2.name,
                fo.address as order_address, fr2.address as restaurant_address,
                fo.restaurant_order_id, count(*) as count_restaurant,
                cp.lng order_lng, cp.lat order_lat,
                cp1.lng restaurant_lng, cp1.lat restaurant_lat,
                cp.hash hash_order
            FROM foodcartapp_restaurantmenuitem fr
                JOIN foodcartapp_product fp2 ON fp2.id = fr.product_id
                JOIN foodcartapp_orderposition fo3 ON fp2.id = fo3.product_id
                JOIN foodcartapp_restaurant fr2 on fr.restaurant_id = fr2.id
                JOIN foodcartapp_order fo on fo.id = fo3.order_id
                JOIN calcdistances_placecoord cp on cp.id = fo.place_id
                JOIN calcdistances_placecoord cp1 on cp1.id = fr2.place_id
            WHERE fr.availability = TRUE
            GROUP by fo3.order_id, restaurant_id
            HAVING count_restaurant = (
                SELECT COUNT(*)
                FROM foodcartapp_orderposition fo4
                GROUP BY fo4.order_id
                HAVING fo4.order_id = fo3.order_id
                )
            ORDER BY order_id
            '''
        )
        order_id = 0
        restaurants = []
        for order in orders_restaurant:
            if order.order_id != order_id:
                order_id = order.order_id
                restaurants = []
            if not order.restaurant_order_id:
                restaurants.append(
                    {
                        'restaurant_id': order.restaurant_id,
                        'name': order.name,
                        'address': order.restaurant_address,
                        'coordinates': {'lng': order.restaurant_lng, 'lat': order.restaurant_lat}
                    }
                )
                restaurants_available.update(
                    {
                        order_id: {
                            'restaurants': restaurants,
                            'address': order.order_address,
                            'coordinates': {'lng': order.order_lng, 'lat': order.order_lat},
                            'hash': order.hash_order
                        },
                    }
                )
            elif order.restaurant_id == order.restaurant_order_id:
                restaurants_available.update(
                    {
                        order_id: {
                            'restaurants':
                                [{'restaurant_id': order.restaurant_order_id,
                                  'name': order.name,
                                  'address': order.restaurant_address,
                                  'coordinates': {'lng': order.restaurant_lng, 'lat': order.restaurant_lat},
                                  'prepare': True}],
                            'address': order.order_address,
                            'coordinates': {'lng': order.order_lng, 'lat': order.order_lat},
                            'hash': order.hash_order
                        }
                    }
                )

        return restaurants_available


class Order(models.Model):
    class Status(models.TextChoices):
        UNPROCESSED = 'UN', _('Необработанный')
        RESTAURANT = 'RS', _('Передан в ресторан')
        COURIER = 'CR', _('Передан курьеру')
        COMPLETED = 'OK', _('Выполнен')

    class PaymentMethod(models.TextChoices):
        CASH = 'CH', _('Наличностью')
        REMOTE = 'RM', _('Электронно')
        EMPTY = 'NO', _('Не назначен')

    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.UNPROCESSED,
        db_index=True,
        verbose_name='статус'
    )
    restaurant_order = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='готовит ресторан'
    )
    payment_method = models.CharField(
        max_length=2,
        choices=PaymentMethod.choices,
        default=PaymentMethod.EMPTY,
        db_index=True,
        verbose_name='способ оплаты'
    )

    firstname = models.CharField(
        max_length=50,
        verbose_name='имя'
    )
    lastname = models.CharField(
        max_length=50,
        verbose_name='фамилия'
    )
    address = models.CharField(
        max_length=255,
        verbose_name='адрес доставки'
    )
    phonenumber = PhoneNumberField(
        db_index=True,
        verbose_name='мобильный телефон'
    )
    registrated_at = models.DateTimeField(
        verbose_name='зарегистрирован',
        default=timezone.now,
        db_index=True
    )
    called_at = models.DateTimeField(
        verbose_name='время звонка',
        blank=True,
        null=True
    )
    delivered_at = models.DateTimeField(
        verbose_name='время доставки',
        blank=True,
        null=True
    )
    products = models.ManyToManyField(
        Product,
        related_name='product_orders',
        through='OrderPosition',
        verbose_name='продукты'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='комментарий'
    )
    place = models.ForeignKey(
        PlaceCoord,
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        ordering = ['called_at', '-registrated_at', 'address']
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.firstname} {self.lastname}: {self.address}'


class OrderPositionQuerySet(models.QuerySet):

    def inner_join(
        self, query,
        field1: str, field2: str,
        values1: list, values2: list
    ):
        query_join = []
        for row1 in self.values(*values1):
            for row2 in query.values(*values2):
                if row1[field1] == row2[field2]:
                    query_join.append(row1 | row2)
        return query_join


class OrderPosition(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='продукт'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='заказ'
    )
    quantity = models.PositiveIntegerField(
        verbose_name='количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    objects = OrderPositionQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'product']
        verbose_name = 'пункт позиции заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f'{self.order} - {self.product.name} - {self.quantity}'
