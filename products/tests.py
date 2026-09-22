from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ProductViewTests(TestCase):
    # Confirm every seeded category page lists its products.
    def test_category_pages_load(self):
        for slug in ('coffee-beans', 'canned-coffee', 'brewing-equipment'):
            response = self.client.get(reverse('product_list_by_category', args=[slug]))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(len(response.context['page_obj']) > 0)

    # Confirm non-bean products have a detail page with only a quantity field.
    def test_detail_page_for_equipment(self):
        product = Product.objects.get(name='French Press')
        response = self.client.get(reverse('product_detail', args=[product.id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('quantity', response.context['form'].fields)
        self.assertNotIn('grind', response.context['form'].fields)

    # Confirm bean products still offer grind and weight choices.
    def test_detail_page_for_beans(self):
        category = Category.objects.get(slug='coffee-beans')
        product = Product.objects.create(name='Test Bean', category=category, description='x', price=Decimal('100'))
        response = self.client.get(reverse('product_detail', args=[product.id]))

        self.assertIn('grind', response.context['form'].fields)
        self.assertIn('weight', response.context['form'].fields)


class CatalogueFeatureTests(TestCase):
    def setUp(self):
        self.category = Category.objects.get(slug='canned-coffee')

    # Confirm search matches names and descriptions across categories.
    def test_search_finds_products(self):
        response = self.client.get(reverse('product_search'), {'q': 'americano'})
        names = {product.name for product in response.context['page_obj']}

        self.assertEqual(names, {'Bold and Strong', 'Pumpkin Punch'})

    # Confirm an empty search returns nothing instead of every product.
    def test_empty_search(self):
        response = self.client.get(reverse('product_search'), {'q': ''})

        self.assertEqual(len(response.context['page_obj']), 0)

    # Confirm products can be sorted by price.
    def test_sort_by_price(self):
        url = reverse('product_list_by_category', args=['canned-coffee'])
        prices = [p.price for p in self.client.get(url, {'sort': 'price_high'}).context['page_obj']]

        self.assertEqual(prices, sorted(prices, reverse=True))

    # Confirm long category lists are split into pages (3 seeded cans + 7 extra = 10 products).
    def test_pagination(self):
        for number in range(7):
            Product.objects.create(name=f'Extra {number}', category=self.category, description='x', price=Decimal('10'))
        url = reverse('product_list_by_category', args=['canned-coffee'])

        first_page = self.client.get(url).context['page_obj']
        self.assertEqual(len(first_page), 6)
        self.assertEqual(first_page.paginator.num_pages, 2)

    # Confirm hidden products are not listed and their detail page is not found.
    def test_unavailable_products_are_hidden(self):
        product = Product.objects.get(name='Moka Pot')
        product.is_available = False
        product.save()

        response = self.client.get(reverse('product_list_by_category', args=['brewing-equipment']))
        self.assertNotIn(product, response.context['page_obj'])
        self.assertEqual(self.client.get(reverse('product_detail', args=[product.id])).status_code, 404)

    # Confirm an out-of-stock product cannot be added to the cart.
    def test_out_of_stock_cannot_be_added(self):
        product = Product.objects.get(name='Moka Pot')
        product.stock = 0
        product.save()

        self.client.post(reverse('cart:add', args=[product.id]), {'quantity': 1})

        self.assertNotIn('cart', self.client.session)
