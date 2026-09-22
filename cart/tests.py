from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

from products.models import Category, Product

from .cart import Cart, MAX_QUANTITY


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
        cart.add(self.product, quantity=2, grind='whole-beans', weight=250)

        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.get_total_price(), Decimal('25.00'))

    # Confirm that setting quantity to zero removes the line.
    def test_zero_quantity_removes_product(self):
        cart = Cart(self.request)
        cart.add(self.product, grind='whole-beans', weight=250)
        cart.update_quantity(Cart.make_line_id(self.product.id, 'whole-beans', 250), 0)

        self.assertEqual(len(cart), 0)

    # Confirm that a larger selected packet uses a proportional final price.
    def test_weight_changes_the_cart_price(self):
        cart = Cart(self.request)
        cart.add(self.product, grind='french-press', weight=1000)

        self.assertEqual(cart.get_total_price(), Decimal('50.00'))

    # Confirm a product without options is priced at its base price.
    def test_product_without_options_uses_base_price(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=3)

        self.assertEqual(cart.get_total_price(), Decimal('37.50'))
        self.assertIn(str(self.product.id), cart.cart)

    # Confirm quantities cannot grow past the cart limit.
    def test_quantity_is_capped(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=MAX_QUANTITY)
        cart.add(self.product, quantity=5)

        self.assertEqual(len(cart), MAX_QUANTITY)


class CartViewTests(TestCase):
    # Create one bean product and one canned coffee product.
    def setUp(self):
        beans, _ = Category.objects.get_or_create(slug='coffee-beans', defaults={'name': 'Coffee Beans'})
        cans, _ = Category.objects.get_or_create(slug='canned-coffee', defaults={'name': 'Canned Coffee'})
        self.bean = Product.objects.create(name='Bean', category=beans, description='x', price=Decimal('100.00'))
        self.can = Product.objects.create(name='Can', category=cans, description='x', price=Decimal('200.00'))

    # Confirm canned coffee can be added with only a quantity.
    def test_add_canned_coffee(self):
        response = self.client.post(reverse('cart:add', args=[self.can.id]), {'quantity': 2})

        self.assertRedirects(response, reverse('cart:detail'))
        self.assertEqual(self.client.session['cart'][str(self.can.id)]['quantity'], 2)

    # Confirm coffee beans still require a valid grind and weight.
    def test_add_beans_requires_options(self):
        response = self.client.post(reverse('cart:add', args=[self.bean.id]), {'quantity': 1})

        self.assertRedirects(response, reverse('product_detail', args=[self.bean.id]))
        self.assertNotIn('cart', self.client.session)

    # Confirm beans are added with the chosen quantity and options.
    def test_add_beans_with_quantity(self):
        self.client.post(reverse('cart:add', args=[self.bean.id]), {
            'quantity': 3, 'grind': 'french-press', 'weight': 500,
        })

        line = self.client.session['cart'][f'{self.bean.id}:french-press:500']
        self.assertEqual(line['quantity'], 3)

    # Confirm update and remove work on cart lines, and bad input does not crash.
    def test_update_and_remove_line(self):
        self.client.post(reverse('cart:add', args=[self.can.id]), {'quantity': 1})
        line_id = str(self.can.id)

        self.client.post(reverse('cart:update', args=[line_id]), {'quantity': 'abc'})
        self.assertEqual(self.client.session['cart'][line_id]['quantity'], 1)

        self.client.post(reverse('cart:update', args=[line_id]), {'quantity': 4})
        self.assertEqual(self.client.session['cart'][line_id]['quantity'], 4)

        self.client.post(reverse('cart:remove', args=[line_id]))
        self.assertEqual(self.client.session['cart'], {})

    # Confirm removing a line that is not in the cart is harmless.
    def test_remove_unknown_line(self):
        response = self.client.post(reverse('cart:remove', args=['999:bad:abc']))

        self.assertRedirects(response, reverse('cart:detail'))
