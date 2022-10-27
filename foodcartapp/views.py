import re
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
        response_err = check_invalid_order(order_data)
        if response_err:
            return Response(response_err, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        order = Order.objects.create(
            phonenumber=order_data['phonenumber'],
            address=order_data['address'],
            firstname=order_data['firstname'],
            lastname=order_data['lastname'],
        )

        positions = [
            OrderPosition(
                order=order,
                product=Product.objects.get(pk=position['product']),
                quantity=position['quantity']
            )
            for position in order_data['products']
        ]
        OrderPosition.objects.bulk_create(positions)

    except ValueError:
        return Response({'error': 'Данные не отправлены'})

    return Response(order_data, status=status.HTTP_201_CREATED)


def check_invalid_order(order_data: dict) -> Union[dict, bool]:
    '''Проверка корректности данных заказа'''

    err_str = 'Поле должно быть строкой'
    keys_type = {
        'products': {'type': (list, tuple), 'err': 'Поле должно содержать список'},
        'firstname': {'type': str, 'err': err_str},
        'lastname': {'type': str, 'err': err_str},
        'phonenumber': {'type': str, 'err': err_str},
        'address': {'type': str, 'err': err_str},
    }

    # проверка на наличие всех ключей
    if len(set(keys_type).intersection(order_data)) < 5:
        no_keys = set(keys_type).difference(order_data)
        return {
            'error': 'Не достаточно данных',
            'fields': {key: 'Это поле обязательно!' for key in list(no_keys)}
        }

    # проверка на вхождение null
    elif None in order_data.values():
        null_keys = [key for key in order_data if order_data[key] is None]
        return {
            'error': 'Не достаточно данных',
            'fields': {key: 'Это поле не должно быть null!' for key in null_keys}
        }

    # проверка типа данных
    elif not all(
        [isinstance(value, keys_type.get(key).get('type'))
         for key, value in order_data.items()]
    ):
        invalid_keys = [
            key for key, value in order_data.items()
            if not isinstance(value, keys_type.get(key).get('type'))
        ]
        return {
            'error': 'Не верные типы данных',
            'fields': {key: keys_type[key]['err'] for key in invalid_keys}
        }

    # проверка на пустые значения
    elif not all(order_data.values()):
        empty_keys = [key for key in order_data if not order_data[key]]
        return {
            'error': 'Не достаточно данных',
            'fields': {key: 'Это поле не должно быть пустым!' for key in empty_keys}
        }

    # проверка корректности номера телефона
    phone_pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
    if not bool(phone_pattern.findall(order_data['phonenumber'])):
        return {'phonenumber': 'Не корректный номер телефона'}

    # Проверка содержания products
    for product in order_data['products']:
        if len({'product', 'quantity'}.intersection(product)) < 2:
            return {'error_products': 'Позиции продукта должны содержать поля product и quantity'}
        if not Product.objects.filter(pk=product.get('product', 0)):
            return {'error_products': 'Не допустимый первичный ключ'}

    return False
