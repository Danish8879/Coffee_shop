from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from products.models import Category, Product

from .models import Order, OrderItem

CHECKOUT_DATA = {
    'first_name': 'Student',
    'last_name': 'User',
    'email': 'student@example.com',
    'address': '123 College Road',
    'phone': '9876543210',
    'payment_method': 'cod',
}


class CheckoutTests(TestCase):
    # Create a user and product that can be used in checkout tests.
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='test-password',
        )
        category, _ = Category.objects.get_or_create(name='Coffee Beans', slug='coffee-beans')
        self.product = Product.objects.create(
            name='Test Coffee',
            category=category,
            description='A test product.',
            price=Decimal('12.50'),
            image='products/test-coffee.jpg',
            stock=10,
        )

    # Confirm checkout creates an order, saves price snapshots, and clears the cart.
    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): {'quantity': 2}}
        session.save()

        response = self.client.post(reverse('orders:checkout'), CHECKOUT_DATA)

        order = Order.objects.get(user=self.user)
        order_item = order.items.get()
        self.assertRedirects(response, reverse('orders:success', args=[order.id]))
        self.assertEqual(order.total_amount, Decimal('25.00'))
        self.assertEqual(order_item.product_name, 'Test Coffee')
        self.assertEqual(order_item.price, Decimal('12.50'))
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.grind, 'whole-beans')
        self.assertEqual(order_item.weight, 250)
        self.assertNotIn('cart', self.client.session)

    # Confirm products without grind and weight are saved on the order without them.
    def test_checkout_with_canned_coffee(self):
        category, _ = Category.objects.get_or_create(slug='canned-coffee', defaults={'name': 'Canned Coffee'})
        can = Product.objects.create(name='Test Can', category=category, description='x', price=Decimal('200.00'))
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[can.id]), {'quantity': 2})

        self.client.post(reverse('orders:checkout'), CHECKOUT_DATA)

        order_item = Order.objects.get(user=self.user).items.get()
        self.assertEqual(order_item.price, Decimal('200.00'))
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.grind, '')
        self.assertIsNone(order_item.weight)

    # Confirm checkout reduces stock across all cart lines of the same product.
    def test_checkout_reduces_stock(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2, 'grind': 'whole-beans', 'weight': 250})
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 3, 'grind': 'french-press', 'weight': 500})

        self.client.post(reverse('orders:checkout'), CHECKOUT_DATA)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    # Confirm checkout is refused and nothing is saved when stock is too low.
    def test_checkout_fails_when_stock_is_too_low(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 5, 'grind': 'whole-beans', 'weight': 250})
        Product.objects.filter(id=self.product.id).update(stock=3)

        response = self.client.post(reverse('orders:checkout'), CHECKOUT_DATA)

        self.assertRedirects(response, reverse('cart:detail'))
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertIn('cart', self.client.session)

    # Confirm the delivery details are saved to the profile and used to prefill the next checkout.
    def test_checkout_saves_details_to_profile(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1, 'grind': 'whole-beans', 'weight': 250})
        self.client.post(reverse('orders:checkout'), CHECKOUT_DATA)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '9876543210')

        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1, 'grind': 'whole-beans', 'weight': 250})
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.context['form'].initial['address'], '123 College Road')

    # Confirm an online order goes to the demo payment page and is confirmed after paying.
    def test_online_payment_flow(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1, 'grind': 'whole-beans', 'weight': 250})

        response = self.client.post(reverse('orders:checkout'), dict(CHECKOUT_DATA, payment_method='online'))
        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('orders:pay', args=[order.id]))

        response = self.client.post(reverse('orders:pay', args=[order.id]))
        order.refresh_from_db()
        self.assertRedirects(response, reverse('orders:success', args=[order.id]))
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.status, Order.Status.CONFIRMED)


class OrderHistoryTests(TestCase):
    # Create two users, each with one order.
    def setUp(self):
        category, _ = Category.objects.get_or_create(slug='canned-coffee', defaults={'name': 'Canned Coffee'})
        self.product = Product.objects.create(name='Can', category=category, description='x', price=Decimal('200'), stock=10)
        self.user = User.objects.create_user(username='a@example.com', password='pass')
        self.other_user = User.objects.create_user(username='b@example.com', password='pass')
        self.order = self._create_order(self.user, quantity=2)
        self.other_order = self._create_order(self.other_user, quantity=1)
        self.client.force_login(self.user)

    def _create_order(self, user, quantity):
        order = Order.objects.create(
            user=user, first_name='A', last_name='B', email=user.username,
            address='Road', phone='9876543210', total_amount=Decimal('200') * quantity,
        )
        OrderItem.objects.create(order=order, product=self.product, product_name='Can', price=Decimal('200'), quantity=quantity)
        return order

    # Confirm users only see their own orders in the history list.
    def test_order_list_shows_only_own_orders(self):
        response = self.client.get(reverse('orders:list'))

        self.assertEqual(list(response.context['orders']), [self.order])

    # Confirm a user cannot open another user's order.
    def test_cannot_view_other_users_order(self):
        response = self.client.get(reverse('orders:detail', args=[self.other_order.id]))

        self.assertEqual(response.status_code, 404)

    # Confirm order pages require login.
    def test_order_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('orders:list'))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('orders:list')}")

    # Confirm a pending order can be cancelled and its stock is returned.
    def test_cancel_pending_order_restores_stock(self):
        response = self.client.post(reverse('orders:cancel', args=[self.order.id]))

        self.assertRedirects(response, reverse('orders:detail', args=[self.order.id]))
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock, 12)

    # Confirm a confirmed order can no longer be cancelled by the customer.
    def test_cannot_cancel_confirmed_order(self):
        self.order.change_status(Order.Status.CONFIRMED)
        self.client.post(reverse('orders:cancel', args=[self.order.id]))

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    # Confirm a user cannot cancel another user's order.
    def test_cannot_cancel_other_users_order(self):
        response = self.client.post(reverse('orders:cancel', args=[self.other_order.id]))

        self.assertEqual(response.status_code, 404)


class OrderStatusTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='a@example.com', password='pass')
        self.order = Order.objects.create(
            user=user, first_name='A', last_name='B', email='a@example.com', address='Road', phone='9876543210',
        )

    # Confirm the normal order flow is allowed.
    def test_valid_status_flow(self):
        self.order.change_status(Order.Status.CONFIRMED)
        self.order.change_status(Order.Status.COMPLETED)

        self.assertEqual(self.order.status, Order.Status.COMPLETED)

    # Confirm steps cannot be skipped and finished orders cannot change.
    def test_invalid_status_changes_are_rejected(self):
        with self.assertRaises(ValueError):
            self.order.change_status(Order.Status.COMPLETED)

        self.order.change_status(Order.Status.CANCELLED)
        with self.assertRaises(ValueError):
            self.order.change_status(Order.Status.CONFIRMED)

    # Confirm cancelling a paid order marks the payment as refunded.
    def test_cancelling_paid_order_refunds(self):
        self.order.payment_method = Order.PaymentMethod.ONLINE
        self.order.save()
        self.order.mark_paid()
        self.order.change_status(Order.Status.CANCELLED)

        self.assertEqual(self.order.payment_status, Order.PaymentStatus.REFUNDED)
