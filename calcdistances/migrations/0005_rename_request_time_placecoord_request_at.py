# Generated by Django 3.2.16 on 2022-11-10 19:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calcdistances', '0004_auto_20221110_1914'),
    ]

    operations = [
        migrations.RenameField(
            model_name='placecoord',
            old_name='request_time',
            new_name='request_at',
        ),
    ]
