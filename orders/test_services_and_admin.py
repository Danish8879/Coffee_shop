from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from products.models import Product

from .models import Order
from .services import OutOfStockError, place_order, remember_delivery_details

DETAILS = {
    'first_name': 'Student', 'last_name': 'User', 'email': 'student@example.com',
    'address': '123 College Road', 'phone': '9876543210',
}


def new_order(**extra):
    return Order(**DETAILS, **extra)


class PlaceOrderServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student@example.com', password='x')
        self.bean = Product.objects.get(name='Harley Estate')
        self.can = Product.objects.get(name='Bold and Strong')

    # Confirm the total and item price snapshots are calculated from weight and quantity.
    def test_totals_and_snapshots(self):
        order = place_order(self.user, new_order(), [
            {'product': self.bean, 'quantity': 2, 'grind': 'espresso-machine', 'weight': 1000},
            {'product': self.can, 'quantity': 3, 'grind': '', 'weight': None},
        ])

        self.assertEqual(order.total_amount, Decimal('5800.00'))
        bean_item = order.items.get(product=self.bean)
        self.assertEqual(bean_item.price, Decimal('2600.00'))
        self.assertEqual(bean_item.get_cost(), Decimal('5200.00'))

    # Confirm later price changes do not change an existing order.
    def test_price_snapshot_is_kept(self):
        order = place_order(self.user, new_order(), [{'product': self.can, 'quantity': 1, 'grind': '', 'weight': None}])
        Product.objects.filter(id=self.can.id).update(price=Decimal('999.00'))

        self.assertEqual(order.items.get().price, Decimal('200.00'))

    # Confirm a hidden product cannot be ordered even if it has stock.
    def test_unavailable_product(self):
        Product.objects.filter(id=self.can.id).update(is_available=False)

        with self.assertRaises(OutOfStockError):
            place_order(self.user, new_order(), [{'product': self.can, 'quantity': 1, 'grind': '', 'weight': None}])
        self.assertFalse(Order.objects.exists())

    # Confirm existing profile details are never overwritten.
    def test_remember_details_keeps_existing_values(self):
        profile = Profile.objects.get(user=self.user)
        profile.phone, profile.address = '1112223334', 'Old address'
        profile.save()

        remember_delivery_details(profile, new_order())

        profile.refresh_from_db()
        self.assertEqual((profile.phone, profile.address), ('1112223334', 'Old address'))


class CheckoutEdgeCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student@example.com', password='x')
        self.can = Product.objects.get(name='Bold and Strong')

    # Confirm checkout requires login and an empty cart is sent back to the cart page.
    def test_login_and_empty_cart(self):
        self.assertEqual(self.client.get(reverse('orders:checkout')).status_code, 302)

        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('orders:checkout')), reverse('cart:detail'))

    # Confirm an invalid phone number keeps the user on the checkout page.
    def test_invalid_phone(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.can.id]), {'quantity': 1})

        response = self.client.post(reverse('orders:checkout'), {**DETAILS, 'phone': '12', 'payment_method': 'cod'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['form'].errors)
        self.assertFalse(Order.objects.exists())

    # Confirm a cash on delivery order stays pending and unpaid, and needs no payment page.
    def test_cash_on_delivery_order(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.can.id]), {'quantity': 1})
        self.client.post(reverse('orders:checkout'), {**DETAILS, 'payment_method': 'cod'})

        order = Order.objects.get()
        self.assertEqual((order.status, order.payment_status), ('pending', 'unpaid'))
        self.assertFalse(order.needs_payment)
        self.assertRedirects(self.client.get(reverse('orders:pay', args=[order.id])), reverse('orders:detail', args=[order.id]))

    # Confirm the order pages render for the owner and the success page is private.
    def test_order_pages_render(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.can.id]), {'quantity': 1})
        self.client.post(reverse('orders:checkout'), {**DETAILS, 'payment_method': 'online'})
        order = Order.objects.get()

        self.assertContains(self.client.get(reverse('orders:pay', args=[order.id])), 'Pay ₹200.00')
        self.assertContains(self.client.get(reverse('orders:detail', args=[order.id])), 'Bold and Strong')
        self.assertContains(self.client.get(reverse('orders:list')), f'#{order.id}')

        other = User.objects.create_user(username='other@example.com', password='x')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('orders:success', args=[order.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('orders:pay', args=[order.id])).status_code, 404)


class OrderAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='x', email='admin@example.com')
        self.customer = User.objects.create_user(username='student@example.com', password='x')
        self.can = Product.objects.get(name='Bold and Strong')
        self.order = place_order(self.customer, new_order(), [{'product': self.can, 'quantity': 4, 'grind': '', 'weight': None}])
        self.client.force_login(self.admin)

    def _run_action(self, action):
        return self.client.post(reverse('admin:orders_order_changelist'), {
            'action': action, '_selected_action': [self.order.id],
        }, follow=True)

    # Confirm the admin order pages load, including the read-only item list.
    def test_admin_pages_load(self):
        self.assertEqual(self.client.get(reverse('admin:orders_order_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:orders_order_change', args=[self.order.id])).status_code, 200)

    # Confirm admin actions follow the allowed status flow.
    def test_status_actions(self):
        response = self._run_action('mark_completed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        self.assertContains(response, 'skipped')

        self._run_action('mark_confirmed')
        self._run_action('mark_completed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

    # Confirm cancelling from admin returns the stock.
    def test_cancel_action_restores_stock(self):
        stock_before_cancel = Product.objects.get(id=self.can.id).stock
        self._run_action('mark_cancelled')

        self.assertEqual(Product.objects.get(id=self.can.id).stock, stock_before_cancel + 4)

    # Confirm the order status cannot be edited directly in the admin form.
    def test_status_is_read_only(self):
        response = self.client.get(reverse('admin:orders_order_change', args=[self.order.id]))

        self.assertNotContains(response, 'name="status"')
