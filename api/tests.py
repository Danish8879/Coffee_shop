from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from orders.models import Order
from products.models import Category, Product

ORDER_DETAILS = {
    'first_name': 'Student',
    'last_name': 'User',
    'email': 'student@example.com',
    'address': '123 College Road',
    'phone': '9876543210',
    'payment_method': 'cod',
}


class ProductApiTests(APITestCase):
    # Confirm anyone can list products and filter them by category.
    def test_list_and_filter_products(self):
        response = self.client.get('/api/products/', {'category': 'canned-coffee'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {product['name'] for product in response.data['results']}
        self.assertEqual(names, {'Bold and Strong', 'Spanish Latte', 'Pumpkin Punch'})

    # Confirm search and ordering query parameters work.
    def test_search_and_ordering(self):
        response = self.client.get('/api/products/', {'search': 'estate', 'ordering': '-price'})
        prices = [Decimal(product['price']) for product in response.data['results']]

        self.assertTrue(prices)
        self.assertEqual(prices, sorted(prices, reverse=True))

    # Confirm hidden products are not returned.
    def test_unavailable_product_is_hidden(self):
        product = Product.objects.get(name='Moka Pot')
        product.is_available = False
        product.save()

        self.assertEqual(self.client.get(f'/api/products/{product.id}/').status_code, status.HTTP_404_NOT_FOUND)

    # Confirm products are read-only through the API.
    def test_products_are_read_only(self):
        response = self.client.post('/api/products/', {'name': 'Hack'})

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))

    # Confirm the categories endpoint lists all categories.
    def test_categories(self):
        slugs = {category['slug'] for category in self.client.get('/api/categories/').data}

        self.assertEqual(slugs, {'coffee-beans', 'canned-coffee', 'brewing-equipment'})


class AuthApiTests(APITestCase):
    # Confirm register returns a token that can be used straight away.
    def test_register_and_use_token(self):
        response = self.client.post('/api/auth/register/', {
            'first_name': 'Student', 'last_name': 'User', 'email': 'New@Example.com', 'password': 'Strong-pass-123',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='new@example.com').exists())

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(self.client.get('/api/profile/').status_code, status.HTTP_200_OK)

    # Confirm weak passwords and duplicate emails are rejected.
    def test_register_validation(self):
        User.objects.create_user(username='taken@example.com', email='taken@example.com', password='x')
        response = self.client.post('/api/auth/register/', {
            'first_name': 'A', 'last_name': 'B', 'email': 'TAKEN@example.com', 'password': '123',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    # Confirm login ignores email case, and logout deletes the token.
    def test_login_and_logout(self):
        User.objects.create_user(username='student@example.com', email='student@example.com', password='Strong-pass-123')
        response = self.client.post('/api/auth/login/', {'email': 'STUDENT@example.com', 'password': 'Strong-pass-123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.exists())

    # Confirm a wrong password is rejected.
    def test_login_wrong_password(self):
        User.objects.create_user(username='student@example.com', password='Strong-pass-123')
        response = self.client.post('/api/auth/login/', {'email': 'student@example.com', 'password': 'wrong'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm the profile can be updated and requires login.
    def test_update_profile(self):
        self.assertEqual(self.client.get('/api/profile/').status_code, status.HTTP_401_UNAUTHORIZED)

        user = User.objects.create_user(username='student@example.com', email='student@example.com', password='x')
        self.client.force_authenticate(user)
        response = self.client.patch('/api/profile/', {'first_name': 'Changed', 'phone': '9876543210'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Changed')
        self.assertEqual(user.profile.phone, '9876543210')

        self.assertEqual(self.client.patch('/api/profile/', {'phone': 'abc'}).status_code, status.HTTP_400_BAD_REQUEST)


class OrderApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student@example.com', email='student@example.com', password='x')
        self.other_user = User.objects.create_user(username='other@example.com', password='x')
        self.staff = User.objects.create_user(username='staff@example.com', password='x', is_staff=True)
        self.bean = Product.objects.create(
            name='Test Bean', category=Category.objects.get(slug='coffee-beans'),
            description='x', price=Decimal('100.00'), stock=10,
        )
        self.can = Product.objects.get(name='Bold and Strong')
        self.client.force_authenticate(self.user)

    def _place_order(self, items, **details):
        return self.client.post('/api/orders/', {**ORDER_DETAILS, **details, 'items': items}, format='json')

    # Confirm an order with beans and a can is created with correct prices and stock is reduced.
    def test_create_order(self):
        response = self._place_order([
            {'product': self.bean.id, 'quantity': 2, 'grind': 'french-press', 'weight': 500},
            {'product': self.can.id, 'quantity': 1},
        ])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('600.00'))
        self.assertEqual(len(response.data['items']), 2)
        self.bean.refresh_from_db()
        self.assertEqual(self.bean.stock, 8)

    # Confirm option rules: beans need options, other products must not have them.
    def test_item_option_validation(self):
        self.assertEqual(self._place_order([{'product': self.bean.id, 'quantity': 1}]).status_code, 400)
        self.assertEqual(
            self._place_order([{'product': self.can.id, 'quantity': 1, 'grind': 'french-press', 'weight': 250}]).status_code,
            400,
        )
        self.assertEqual(self._place_order([]).status_code, 400)
        self.assertFalse(Order.objects.exists())

    # Confirm ordering more than the stock fails without creating an order.
    def test_out_of_stock(self):
        response = self._place_order([{'product': self.bean.id, 'quantity': 11, 'grind': 'whole-beans', 'weight': 250}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    # Confirm customers only see their own orders, while staff see everyone's.
    def test_order_visibility(self):
        self._place_order([{'product': self.can.id, 'quantity': 1}])
        self.client.force_authenticate(self.other_user)
        self._place_order([{'product': self.can.id, 'quantity': 1}])
        own_order = Order.objects.get(user=self.user)

        self.assertEqual(self.client.get('/api/orders/').data['count'], 1)
        self.assertEqual(self.client.get(f'/api/orders/{own_order.id}/').status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get('/api/orders/').data['count'], 2)

    # Confirm orders require login.
    def test_orders_require_login(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get('/api/orders/').status_code, status.HTTP_401_UNAUTHORIZED)

    # Confirm a pending order can be cancelled once and its stock is returned.
    def test_cancel(self):
        order_id = self._place_order([{'product': self.can.id, 'quantity': 2}]).data['id']
        stock_after_order = Product.objects.get(id=self.can.id).stock

        response = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(Product.objects.get(id=self.can.id).stock, stock_after_order + 2)
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/cancel/').status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm the demo payment confirms an online order.
    def test_pay_online_order(self):
        order_id = self._place_order([{'product': self.can.id, 'quantity': 1}], payment_method='online').data['id']

        response = self.client.post(f'/api/orders/{order_id}/pay/')
        self.assertEqual(response.data['payment_status'], 'paid')
        self.assertEqual(response.data['status'], 'confirmed')
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/pay/').status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm staff cannot pay or cancel an order on the customer's behalf.
    def test_staff_cannot_pay_customers_order(self):
        order_id = self._place_order([{'product': self.can.id, 'quantity': 1}], payment_method='online').data['id']
        self.client.force_authenticate(self.staff)

        self.assertEqual(self.client.post(f'/api/orders/{order_id}/pay/').status_code, status.HTTP_403_FORBIDDEN)

    # Confirm only staff can change status, and only along the allowed flow.
    def test_change_status(self):
        order_id = self._place_order([{'product': self.can.id, 'quantity': 1}]).data['id']
        url = f'/api/orders/{order_id}/status/'

        self.assertEqual(self.client.post(url, {'status': 'confirmed'}).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(url, {'status': 'completed'}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(url, {'status': 'confirmed'}).data['status'], 'confirmed')
        self.assertEqual(self.client.post(url, {'status': 'completed'}).data['status'], 'completed')


class ApiDocsTests(APITestCase):
    # Confirm the OpenAPI schema and Swagger page load.
    def test_docs_load(self):
        self.assertEqual(self.client.get('/api/schema/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/docs/').status_code, status.HTTP_200_OK)
