# Generated by Django 3.2.16 on 2022-10-29 07:49

from django.db import migrations


def copy_price_from_product_to_orderposition(apps, schema_editor):
    Product = apps.get_model('foodcartapp', 'Product')
    OrderPosition = apps.get_model('foodcartapp', 'OrderPosition')
    for product in Product.objects.all():
        positions = product.positions.all()
        for position in positions:
            position.price = product.price
        OrderPosition.objects.bulk_update(positions, ['price'])


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0040_orderposition_price'),
    ]

    operations = [
        migrations.RunPython(copy_price_from_product_to_orderposition)
    ]
