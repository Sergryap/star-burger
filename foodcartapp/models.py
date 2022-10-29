from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum, F, OuterRef, Subquery
from phonenumber_field.modelfields import PhoneNumberField


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
            .select_related('product')
            .select_related('order')
            .values('order_id')
            .annotate(total=Sum(F('product__price') * F('quantity')))
            .order_by()
            .values('order', 'total')
            .filter(order=OuterRef('pk'))
        )
        orders = (
            Order.objects
            .annotate(total=Subquery(cost.values('total')))
            .order_by('created_at')
        )

        return orders


class Order(models.Model):
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
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='создан'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='изменен'
    )
    products = models.ManyToManyField(
        Product,
        related_name='product_orders',
        through='OrderPosition',
        verbose_name='продукты',
    )
    objects = OrderQuerySet.as_manager()

    class Meta:
        ordering = ['updated_at', 'address']
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

    class Meta:
        ordering = ['order', 'product']
        verbose_name = 'пункт позиции заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f'{self.order} - {self.product.name} - {self.quantity}'
