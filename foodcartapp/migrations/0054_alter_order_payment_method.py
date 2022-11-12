# Generated by Django 3.2.16 on 2022-11-10 16:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0053_alter_orderposition_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('CH', 'Наличностью'), ('RM', 'Электронно'), ('NO', 'Не назначен')], db_index=True, default='NO', max_length=2, verbose_name='способ оплаты'),
        ),
    ]