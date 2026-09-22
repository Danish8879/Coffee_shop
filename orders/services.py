import logging
from collections import Counter

from django.db import transaction

from products.models import Product

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class OutOfStockError(Exception):
    pass


# Lock the ordered products and reduce their stock, or raise OutOfStockError if any are short.
def _reserve_stock(lines):
    needed = Counter()
    for line in lines:
        needed[line['product'].id] += line['quantity']

    products = list(Product.objects.select_for_update().filter(id__in=needed))
    for product in products:
        if not product.is_available or product.stock < needed[product.id]:
            raise OutOfStockError(f'Only {product.stock} unit(s) of {product.name} left in stock.')

    for product in products:
        product.stock -= needed[product.id]
        product.save(update_fields=['stock'])


# Create an order with its items and reserve stock in one transaction.
# Used by both the website checkout and the REST API.
# `order` is an unsaved Order with the delivery details filled in; each line needs
# product, quantity, grind and weight.
def place_order(user, order, lines):
    with transaction.atomic():
        _reserve_stock(lines)

        order.user = user
        order.total_amount = sum(
            (line['product'].get_price_for_weight(line['weight']) * line['quantity'] for line in lines),
        )
        order.save()

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=line['product'],
                product_name=line['product'].name,
                price=line['product'].get_price_for_weight(line['weight']),
                quantity=line['quantity'],
                grind=line['grind'] or '',
                weight=line['weight'],
            )
            for line in lines
        ])

    logger.info('Order #%s placed by %s for %s', order.id, user.username, order.total_amount)
    return order


# Save the delivery details on the user's profile the first time they order.
def remember_delivery_details(profile, order):
    if profile.phone and profile.address:
        return
    profile.phone = profile.phone or order.phone
    profile.address = profile.address or order.address
    profile.save(update_fields=['phone', 'address', 'updated_at'])
