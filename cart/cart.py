from decimal import Decimal

from products.models import Product


class Cart:
    session_key = 'cart'

    # Load the cart dictionary from the current visitor's session.
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(self.session_key, {})
        self._normalise_legacy_items()

    # Convert cart items saved before grind and weight options were introduced.
    def _normalise_legacy_items(self):
        normalised_cart = {}
        changed = False

        for line_id, item in self.cart.items():
            if 'product_id' not in item:
                product_id = line_id
                grind = 'whole-beans'
                weight = 250
                changed = True
            else:
                product_id = str(item['product_id'])
                grind = item.get('grind', 'whole-beans')
                weight = int(item.get('weight', 250))

            normalised_line_id = f'{product_id}:{grind}:{weight}'
            normalised_cart[normalised_line_id] = {
                'product_id': product_id,
                'grind': grind,
                'weight': weight,
                'quantity': item['quantity'],
            }

        if changed:
            self.cart = normalised_cart
            self.save()

    # Store the current cart contents in the visitor's session.
    def save(self):
        self.session[self.session_key] = self.cart
        self.session.modified = True

    # Add a product or increase the quantity of a product already in the cart.
    def add(self, product, quantity=1, grind='whole-beans', weight=250, override_quantity=False):
        product_id = str(product.id)
        quantity = max(int(quantity), 1)
        weight = int(weight)
        line_id = f'{product_id}:{grind}:{weight}'

        if line_id not in self.cart:
            self.cart[line_id] = {
                'product_id': product_id,
                'grind': grind,
                'weight': weight,
                'quantity': 0,
            }

        if override_quantity:
            self.cart[line_id]['quantity'] = quantity
        else:
            self.cart[line_id]['quantity'] += quantity

        self.save()

    # Remove one product entirely from the cart.
    def remove(self, product, grind='whole-beans', weight=250):
        line_id = f'{product.id}:{grind}:{int(weight)}'
        if line_id in self.cart:
            del self.cart[line_id]
            self.save()

    # Replace a product's quantity or remove it when the quantity is zero.
    def update_quantity(self, product, quantity, grind='whole-beans', weight=250):
        quantity = int(quantity)
        if quantity <= 0:
            self.remove(product, grind=grind, weight=weight)
            return

        self.add(product, quantity=quantity, grind=grind, weight=weight, override_quantity=True)

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

    # Empty the cart after a future successful checkout.
    def clear(self):
        self.session.pop(self.session_key, None)
        self.session.modified = True
