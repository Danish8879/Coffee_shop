from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from products.models import Product

from .cart import Cart


class CartEdgeCaseTests(TestCase):
    # Build a request with a writable session and pick two seeded products.
    def setUp(self):
        self.request = RequestFactory().get('/')
        SessionMiddleware(lambda request: None).process_request(self.request)
        self.request.session.save()
        self.bean = Product.objects.get(name='Araku Estate')
        self.can = Product.objects.get(name='Spanish Latte')

    # Confirm the same bean with different options is kept as separate cart lines.
    def test_different_options_are_separate_lines(self):
        cart = Cart(self.request)
        cart.add(self.bean, grind='whole-beans', weight=250)
        cart.add(self.bean, grind='french-press', weight=250)
        cart.add(self.bean, grind='whole-beans', weight=250)

        self.assertEqual(len(cart.cart), 2)
        self.assertEqual(len(cart), 3)

    # Confirm carts saved in the old format are converted to the new line format.
    def test_legacy_cart_is_converted(self):
        self.request.session['cart'] = {str(self.bean.id): {'quantity': 2}}
        cart = Cart(self.request)

        line_id = Cart.make_line_id(self.bean.id, 'whole-beans', 250)
        self.assertEqual(cart.cart[line_id]['quantity'], 2)
        self.assertEqual(cart.get_total_price(), Decimal('1100.00'))

    # Confirm a product deleted from the shop is skipped instead of crashing the cart.
    def test_deleted_product_is_skipped(self):
        self.request.session['cart'] = {
            '99999': {'product_id': '99999', 'grind': '', 'weight': None, 'quantity': 1},
        }
        cart = Cart(self.request)

        self.assertEqual(list(cart), [])
        self.assertEqual(cart.get_total_price(), Decimal('0.00'))

    # Confirm updating a line with a very large quantity is capped at the limit.
    def test_update_quantity_is_capped(self):
        cart = Cart(self.request)
        cart.add(self.can)
        cart.update_quantity(str(self.can.id), 500)

        self.assertEqual(len(cart), 20)

    # Confirm updating a line that is not in the cart does nothing.
    def test_update_unknown_line(self):
        cart = Cart(self.request)
        cart.update_quantity('does-not-exist', 3)

        self.assertEqual(len(cart), 0)

    # Confirm clearing the cart removes it from the session.
    def test_clear(self):
        cart = Cart(self.request)
        cart.add(self.can)
        cart.clear()

        self.assertNotIn('cart', self.request.session)


class CartPageTests(TestCase):
    # Confirm the cart page shows lines, the total and a login link for visitors.
    def test_cart_page_shows_total(self):
        can = Product.objects.get(name='Spanish Latte')
        self.client.post(reverse('cart:add', args=[can.id]), {'quantity': 2})

        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Spanish Latte')
        self.assertContains(response, 'Total: ₹600.00')
        self.assertContains(response, 'Log in to checkout')

    # Confirm the empty cart message is shown.
    def test_empty_cart(self):
        self.assertContains(self.client.get(reverse('cart:detail')), 'Your cart is empty.')

    # Confirm cart changes must be POST requests.
    def test_cart_actions_need_post(self):
        can = Product.objects.get(name='Spanish Latte')

        self.assertEqual(self.client.get(reverse('cart:add', args=[can.id])).status_code, 405)
        self.assertEqual(self.client.get(reverse('cart:remove', args=[str(can.id)])).status_code, 405)

    # Confirm adding a product that does not exist returns 404.
    def test_add_missing_product(self):
        self.assertEqual(self.client.post(reverse('cart:add', args=[99999]), {'quantity': 1}).status_code, 404)
