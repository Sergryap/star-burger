from django.utils.translation import gettext_lazy as _
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum, F, OuterRef, Subquery, Prefetch, Count
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone


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
    def add_total_cost():
        cost = (
            OrderPosition.objects
            .values('order_id')
            .annotate(total=Sum(F('price') * F('quantity')))
            .filter(order=OuterRef('pk'))
        )
        orders = (
            Order.objects
            .defer(
                'restaurant_order',
                'registrated_at',
                'called_at',
                'delivered_at',
            )
            .annotate(total=Subquery(cost.values('total')))
            .order_by('called_at', '-registrated_at')
        )

        return orders

    @staticmethod
    def get_restaurants_available():
        restaurants_available = {}
        orders_restaurant = RestaurantMenuItem.objects.raw(
            '''
            SELECT id, order_id, restaurant_id, name, order_address, restaurant_address, restaurant_order_id
            FROM
            (
            SELECT fr.id, restaurant_id, fo3.order_id, fr2.name, fo.address as order_address, fr2.address as restaurant_address, fo.restaurant_order_id, count(*) as count_restaurant
            FROM foodcartapp_restaurantmenuitem fr
            JOIN foodcartapp_product fp2 ON fp2.id = fr.product_id
            JOIN foodcartapp_orderposition fo3 ON fp2.id = fo3.product_id
            JOIN foodcartapp_restaurant fr2 on fr.restaurant_id = fr2.id
            JOIN foodcartapp_order fo on fo.id = fo3.order_id
            WHERE fr.availability = TRUE
            GROUP by fo3.order_id, restaurant_id
            HAVING count_restaurant = (
                select COUNT(*)
                from foodcartapp_orderposition fo4
                group by fo4.order_id
                HAVING fo4.order_id = fo3.order_id
                )
            )
            GROUP BY order_id, restaurant_id
            '''
        )
        order_id = 0
        restaurants = []
        for order in list(orders_restaurant):
            if order.order_id != order_id:
                order_id = order.order_id
                restaurants = []
            if not order.restaurant_order_id:
                restaurants.append(
                    {'restaurant': order.restaurant_order_id,
                     'name': order.name,
                     'address': order.restaurant_address}
                )

                restaurants_available.update(
                    {order_id: {
                        'restaurants': restaurants,
                        'address': order.order_address}}
                )
            else:
                if order.restaurant_id == order.restaurant_order_id:
                    restaurants_available.update(
                        {order_id: {
                            'restaurants':
                                [{'restaurant': order.restaurant_order_id,
                                  'name': order.name,
                                  'address': order.restaurant_address,
                                  'prepare': True}],
                            'address': order.order_address}}
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
        default=PaymentMethod.CASH,
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
