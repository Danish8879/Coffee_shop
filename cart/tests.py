from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.contrib.sessions.middleware import SessionMiddleware

from products.models import Category, Product

from .cart import Cart


class CartTests(TestCase):
    # Build a request with a writable session for cart unit tests.
    def setUp(self):
        self.request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(self.request)
        self.request.session.save()

        category, _ = Category.objects.get_or_create(name='Coffee Beans', slug='coffee-beans')
        self.product = Product.objects.create(
            name='Test Coffee',
            category=category,
            description='A test product.',
            price=Decimal('12.50'),
            image='products/test-coffee.jpg',
        )

    # Confirm that adding a product records its quantity and total price.
    def test_add_product_and_calculate_total(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2)

        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.get_total_price(), Decimal('25.00'))

    # Confirm that setting quantity to zero removes the product.
    def test_zero_quantity_removes_product(self):
        cart = Cart(self.request)
        cart.add(self.product)
        cart.update_quantity(self.product, 0)

        self.assertEqual(len(cart), 0)

    # Confirm that a larger selected packet uses a proportional final price.
    def test_weight_changes_the_cart_price(self):
        cart = Cart(self.request)
        cart.add(self.product, grind='french-press', weight=1000)

        self.assertEqual(cart.get_total_price(), Decimal('50.00'))
