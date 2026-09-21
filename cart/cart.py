from decimal import Decimal

from products.models import Product


class Cart:
    session_key = 'cart'

    # Load the cart dictionary from the current visitor's session.
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(self.session_key, {})

    # Store the current cart contents in the visitor's session.
    def save(self):
        self.session[self.session_key] = self.cart
        self.session.modified = True

    # Add a product or increase the quantity of a product already in the cart.
    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        quantity = max(int(quantity), 1)

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0}

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        self.save()

    # Remove one product entirely from the cart.
    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    # Replace a product's quantity or remove it when the quantity is zero.
    def update_quantity(self, product, quantity):
        quantity = int(quantity)
        if quantity <= 0:
            self.remove(product)
            return

        self.add(product, quantity=quantity, override_quantity=True)

    # Yield cart entries together with their current product information.
    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            cart_item = cart[str(product.id)]
            cart_item['product'] = product
            cart_item['total_price'] = product.price * cart_item['quantity']
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
