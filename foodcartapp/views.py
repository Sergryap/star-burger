from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.response import Response
from foodcartapp.models import Product, Order, OrderPosition
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.serializers import ModelSerializer, ListField, IntegerField
from django.db import transaction


class OrderSerializer(ModelSerializer):
    products = ListField(allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'address', 'phonenumber', 'products']


class OrderPositionSerializer(ModelSerializer):
    quantity = IntegerField(min_value=1)

    class Meta:
        model = OrderPosition
        fields = ['product', 'quantity']


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@transaction.atomic
@api_view(['POST'])
def register_order(request):
    order_data = request.data

    order_serializer = OrderSerializer(data=order_data)
    order_serializer.is_valid(raise_exception=True)
    for product in order_data['products']:
        product_serializer = OrderPositionSerializer(data=product)
        product_serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        phonenumber=order_data['phonenumber'],
        address=order_data['address'],
        firstname=order_data['firstname'],
        lastname=order_data['lastname'],
    )

    positions = []
    products = {
        product.pk: product
        for product in Product.objects.filter(pk__in=[pk['product'] for pk in order_data['products']])
    }

    for position in order_data['products']:
        product = products[position['product']]
        positions.append(
            OrderPosition(
                order=order,
                product=product,
                price=product.price,
                quantity=position['quantity']
            )
        )

    OrderPosition.objects.bulk_create(positions)
    out_serializer = OrderSerializer(instance=order)

    return Response(out_serializer.data, status=status.HTTP_201_CREATED)
