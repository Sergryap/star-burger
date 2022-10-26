from typing import Union
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.response import Response
from .models import Product, Order, OrderPosition
from rest_framework.decorators import api_view
from rest_framework import status


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
        invalid_data = check_invalid_data(order_data)
        if invalid_data:
            return Response(invalid_data, status=status.HTTP_405_METHOD_NOT_ALLOWED)

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

    return Response(order_data, status=status.HTTP_201_CREATED)


def check_invalid_data(order_data: dict) -> Union[dict, bool]:
    invalid_data = None

    if order_data.get('products') is not None:

        if not isinstance(order_data.get('products'), (list, tuple)):
            invalid_data = {
                'error': 'Ожидался list со значениями, но был получен str',
                'products': order_data["products"]
            }
        elif not order_data['products']:
            invalid_data = {
                'error': 'Этот список не может быть пустым',
                'products': order_data["products"]
            }

    elif order_data.get('products', 0) == 0:
        invalid_data = {
            'error': 'Это обязательное поле',
            'products': '[products]'
        }

    elif order_data['products'] is None:
        invalid_data = {
            'error': 'Это поле не может быть пустым',
            'products': order_data["products"]
        }

    if len({'firstname', 'lastname', 'phonenumber', 'address'}.intersection(set(order_data))) != 4:
        invalid_data = {
            'error': 'Не достаточно данных',
        }

    if invalid_data:
        return invalid_data
    else:
        return False
