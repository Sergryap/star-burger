from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
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

    @staticmethod
    def add_data_order(order_id, order, prepare):

        status = {
            'UN': 'Необработанный',
            'RS': 'Передан в ресторан',
            'CR': 'Передан курьеру',
            'OK': 'Выполнен',
            'CH': 'Наличностью',
            'RM': 'Электронно',
            'NO': 'Не назначен',
        }
        return {
            'address': order.order_address,
            'hash': order.hash_order,
            'pk': order_id,
            'status': status[order.status],
            'payment_method': status[order.payment_method],
            'phone': order.phone,
            'client': f'{order.first_name} {order.last_name}',
            'total_cost': order.total_cost,
            'comment': order.order_comment,
            'prepare': prepare,
            'order_position_id': order.order_position_id
        }

    def get_data_orders(self):
        restaurants_available = {}
        orders_restaurant = self.raw(
            '''
            select *
            from (
            select
                fr2.id, restaurant_id, fo.id as order_id, fr2.name,
                (array_agg(fo3.id))[1] as order_position_id,
                fo.address as order_address, fr2.address as restaurant_address,
                fo.restaurant_order_id, COUNT(*) as count_restaurant,
                cp.lng order_lng, cp.lat order_lat,
                cp1.lng restaurant_lng, cp1.lat restaurant_lat,
                cp.hash hash_order, cp1.hash hash_restaurant,
                fo.status, fo.payment_method, fo.called_at,
                fo.firstname as first_name, fo.lastname as last_name,
                fo.phonenumber as phone, fo.comment as order_comment,
                round((acos(sind(cp.lat)*sind(cp1.lat)
                       +cosd(cp.lat)*cosd(cp1.lat)*cosd(cp.lng
                       -cp1.lng))*6371)::numeric, 2) as dist,
                (SELECT SUM(quantity*price)
                FROM foodcartapp_orderposition
                GROUP BY order_id
                HAVING order_id = fo.id) as total_cost
            FROM foodcartapp_order fo
            LEFT JOIN foodcartapp_orderposition fo3 ON fo.id = fo3.order_id
            LEFT JOIN foodcartapp_product fp2 ON fp2.id = fo3.product_id
            LEFT JOIN foodcartapp_restaurantmenuitem fr ON fr.product_id = fp2.id
            LEFT JOIN foodcartapp_restaurant fr2 ON fr2.id = fr.restaurant_id
            LEFT JOIN calcdistances_placecoord cp ON cp.id = fo.place_id
            LEFT JOIN calcdistances_placecoord cp1 ON cp1.id = fr2.place_id
            WHERE (fr.availability = TRUE OR fo3.order_id ISNULL) and fo.status != 'OK'
            group by
                fo.id, fr2.name, restaurant_id, fr2.id,
                fo.address, fr2.address, cp.lng, cp.lat, cp1.lng, cp1.lat,
                cp.hash, cp1.hash
            ) as foo
            where
                foo.count_restaurant = (
                    SELECT COUNT(*)
                    from foodcartapp_orderposition fo4
                    GROUP BY fo4.order_id
                    HAVING fo4.order_id = foo.order_id
                    )
                or foo.order_position_id ISNULL
            ORDER BY foo.called_at DESC, foo.order_id, foo.dist
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
                        'hash': order.hash_restaurant,
                        'dist': order.dist,

                    }
                )
                restaurants_available.update(
                    {
                        order_id: {
                            'restaurants': restaurants
                        } | self.add_data_order(order_id, order, prepare=False)
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
                                  'hash': order.hash_restaurant,
                                  'dist': order.dist}]
                        } | self.add_data_order(order_id, order, prepare=True)
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

    class Meta:
        ordering = ['order', 'product']
        verbose_name = 'пункт позиции заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f'{self.order} - {self.product.name} - {self.quantity}'
