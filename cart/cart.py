from decimal import Decimal

from products.models import Product

MAX_QUANTITY = 20


class Cart:
    session_key = 'cart'

    # Load the cart dictionary from the current visitor's session.
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(self.session_key, {})
        self._normalise_legacy_items()

    # Convert cart items saved before grind and weight options were introduced.
    def _normalise_legacy_items(self):
        legacy_ids = [line_id for line_id, item in self.cart.items() if 'product_id' not in item]
        if not legacy_ids:
            return

        for product_id in legacy_ids:
            item = self.cart.pop(product_id)
            line_id = self.make_line_id(product_id, 'whole-beans', 250)
            self.cart[line_id] = {
                'product_id': str(product_id),
                'grind': 'whole-beans',
                'weight': 250,
                'quantity': item['quantity'],
            }
        self.save()

    # Build the key for one cart line; the same product with different options is a separate line.
    @staticmethod
    def make_line_id(product_id, grind='', weight=None):
        if weight is None:
            return str(product_id)
        return f'{product_id}:{grind}:{weight}'

    # Store the current cart contents in the visitor's session.
    def save(self):
        self.session[self.session_key] = self.cart
        self.session.modified = True

    # Add a product or increase the quantity of a line already in the cart.
    # Coffee beans pass a grind and weight; other products leave them empty.
    def add(self, product, quantity=1, grind='', weight=None):
        product_id = str(product.id)
        weight = int(weight) if weight is not None else None
        line_id = self.make_line_id(product_id, grind, weight)

        if line_id not in self.cart:
            self.cart[line_id] = {
                'product_id': product_id,
                'grind': grind,
                'weight': weight,
                'quantity': 0,
            }

        new_quantity = self.cart[line_id]['quantity'] + max(int(quantity), 1)
        self.cart[line_id]['quantity'] = min(new_quantity, MAX_QUANTITY)
        self.save()

    # Remove one cart line entirely.
    def remove(self, line_id):
        if line_id in self.cart:
            del self.cart[line_id]
            self.save()

    # Replace a line's quantity or remove it when the quantity is zero or less.
    def update_quantity(self, line_id, quantity):
        if line_id not in self.cart:
            return

        quantity = int(quantity)
        if quantity <= 0:
            self.remove(line_id)
            return

        self.cart[line_id]['quantity'] = min(quantity, MAX_QUANTITY)
        self.save()

    # Yield cart entries together with their current product information.
    def __iter__(self):
        product_ids = {item['product_id'] for item in self.cart.values()}
        products = {str(product.id): product for product in Product.objects.filter(id__in=product_ids)}

        for line_id, stored_item in self.cart.items():
            product = products.get(stored_item['product_id'])
            if product is None:
                continue

            cart_item = stored_item.copy()
            cart_item['line_id'] = line_id
            cart_item['product'] = product
            cart_item['unit_price'] = product.get_price_for_weight(cart_item['weight'])
            cart_item['total_price'] = cart_item['unit_price'] * cart_item['quantity']
            yield cart_item

    # Return the number of product units currently in the cart.
    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    # Calculate the cart total using the products' current prices.
    def get_total_price(self):
        return sum((item['total_price'] for item in self), Decimal('0.00'))

    # Empty the cart after a successful checkout.
    def clear(self):
        self.session.pop(self.session_key, None)
        self.session.modified = True
