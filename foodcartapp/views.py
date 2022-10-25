import json

from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.response import Response

from .models import Product, Order, OrderPosition
from rest_framework.decorators import api_view


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


@api_view(['POST'])
def register_order(request):
    try:
        order_data = request.data
        order = Order.objects.create(
            phonenumber=order_data['phonenumber'],
            address=order_data['address'],
            firstname=order_data['firstname'],
            lastname=order_data['lastname'],
        )

        for position in order_data['products']:
            product = Product.objects.get(pk=position['product'])
            OrderPosition.objects.create(
                product=product,
                order=order,
                quantity=position['quantity'],
            )

    except ValueError:
        return Response({
            'error': 'Данные не отправлены',
        })
    return Response(order_data)
