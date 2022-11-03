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
        orders = (
            Order.objects.all()
            .select_related('restaurant_order')
            .only(
                'address',
                'restaurant_order',
                'restaurant_order__name',
                'restaurant_order__address'
            )
            .prefetch_related(
                Prefetch('products', Product.objects.only('pk'))
            )
        )
        restaurants_available = {}

        for order in orders:
            if not order.restaurant_order:
                restaurants = list(
                    RestaurantMenuItem.objects
                    .select_related('restaurant')
                    .defer('restaurant__contact_phone')
                    .filter(availability=True, product__in=order.products.all())
                    .values('restaurant')
                    .annotate(count_products=Count('restaurant'))
                    .filter(count_products=order.products.count())
                    .values(
                        'restaurant',
                        name=F('restaurant__name'),
                        address=F('restaurant__address')
                    )
                )
                restaurants_available.update(
                    {order.pk: {
                        'restaurants': restaurants,
                        'address': order.address}}
                )
            else:
                restaurants_available.update(
                    {order.pk: {
                        'restaurants':
                            [{'restaurant': order.restaurant_order.pk,
                              'name': order.restaurant_order.name,
                              'address': order.restaurant_order.address,
                              'prepare': True}],
                        'address': order.address}}
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
        verbose_name='количество'
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
