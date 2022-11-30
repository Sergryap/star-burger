from django import template
from django.conf.global_settings import ALLOWED_HOSTS
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

register = template.Library()


@register.filter
def link_edit_orders(value):
    url = f"{reverse('admin:foodcartapp_order_change', args=(value['pk'],))}?next={reverse('restaurateur:view_orders')}"
    url_allowed = url_has_allowed_host_and_scheme(url, allowed_hosts=ALLOWED_HOSTS)
    if url_allowed:
        return url
    return '#'

