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
    required_data = {'products', 'firstname', 'lastname', 'phonenumber', 'address'}

    # проверка на наличие всех ключей
    if len(required_data.intersection(set(order_data))) < 5:
        no_data = required_data.difference(set(order_data))
        invalid_data = {'error': 'Не достаточно данных'}
        invalid_data.update({position: 'Это поле обязательно!' for position in list(no_data)})

    # проверка всех позиций на вхождение null
    elif None in order_data.values():
        null_data = [name for name in order_data if order_data[name] is None]
        invalid_data = {'error': 'Не достаточно данных'}
        invalid_data.update({position: 'Это поле не должно быть пустым!' for position in null_data})

    # проверка на пустые значения всех позиций
    elif (
        not all(order_data.values())
        and all([isinstance(value, str) for key, value in order_data.items() if key != 'products'])
    ):
        empty_data = [name for name in order_data if not order_data[name]]
        invalid_data = {'error': 'Не достаточно данных'}
        invalid_data.update({position: 'Это поле не должно быть пустым!' for position in empty_data})

    # проверка типа данных для 'products'
    elif not isinstance(order_data.get('products'), (list, tuple)):
        invalid_data = {
            'error': 'Ожидался list со значениями, но был получен str',
            'products': order_data["products"]
        }

    # проверка типа данных позиций, кроме 'products'
    elif not all([isinstance(value, str) for key, value in order_data.items() if key != 'products']):
        non_type_data = [key for key, value in order_data.items() if not isinstance(value, str) and key != 'products']
        invalid_data = {'error': 'Не верные типы данных'}
        invalid_data.update({position: 'Поле должно быть строкой!' for position in non_type_data})

    if invalid_data:
        return invalid_data
    else:
        return False
