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
            self.assertTrue(response.context['products'].exists())

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
