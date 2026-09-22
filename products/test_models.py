from decimal import Decimal

from django.test import TestCase

from .forms import ProductOptionsForm, QuantityForm, get_add_to_cart_form
from .models import Category, Product


class SeedDataTests(TestCase):
    # Confirm the data migrations create the starter catalogue.
    def test_seeded_catalogue(self):
        counts = {category.slug: category.products.count() for category in Category.objects.all()}

        self.assertEqual(counts, {'coffee-beans': 5, 'canned-coffee': 3, 'brewing-equipment': 2})
        self.assertEqual(Product.objects.get(name='Moka Pot').price, Decimal('2000.00'))


class ProductModelTests(TestCase):
    def setUp(self):
        self.bean = Product.objects.get(name='Araku Estate')
        self.equipment = Product.objects.get(name='French Press')

    # Confirm bean prices scale with packet weight from the 250 g base price.
    def test_price_for_weight(self):
        self.assertEqual(self.bean.get_price_for_weight(250), Decimal('550.00'))
        self.assertEqual(self.bean.get_price_for_weight(500), Decimal('1100.00'))
        self.assertEqual(self.bean.get_price_for_weight(750), Decimal('1650.00'))
        self.assertEqual(self.bean.get_price_for_weight(1000), Decimal('2200.00'))

    # Confirm products without a weight use their base price.
    def test_price_without_weight(self):
        self.assertEqual(self.equipment.get_price_for_weight(None), Decimal('1500.00'))

    # Confirm only coffee beans have grind and weight options.
    def test_has_bean_options(self):
        self.assertTrue(self.bean.has_bean_options)
        self.assertFalse(self.equipment.has_bean_options)

    # Confirm a product is in stock only when it is available and has units left.
    def test_in_stock(self):
        self.assertTrue(self.equipment.in_stock)

        self.equipment.stock = 0
        self.assertFalse(self.equipment.in_stock)

        self.equipment.stock = 5
        self.equipment.is_available = False
        self.assertFalse(self.equipment.in_stock)


class AddToCartFormTests(TestCase):
    # Confirm the right form is chosen for each kind of product.
    def test_form_matches_product(self):
        self.assertIsInstance(get_add_to_cart_form(Product.objects.get(name='Araku Estate')), ProductOptionsForm)
        self.assertIsInstance(get_add_to_cart_form(Product.objects.get(name='Moka Pot')), QuantityForm)
        self.assertNotIsInstance(get_add_to_cart_form(Product.objects.get(name='Moka Pot')), ProductOptionsForm)

    # Confirm quantity must be between 1 and 20.
    def test_quantity_limits(self):
        self.assertFalse(QuantityForm({'quantity': 0}).is_valid())
        self.assertFalse(QuantityForm({'quantity': 21}).is_valid())
        self.assertTrue(QuantityForm({'quantity': 20}).is_valid())

    # Confirm unknown grind and weight values are rejected.
    def test_invalid_bean_options(self):
        self.assertFalse(ProductOptionsForm({'quantity': 1, 'grind': 'powder', 'weight': 250}).is_valid())
        self.assertFalse(ProductOptionsForm({'quantity': 1, 'grind': 'french-press', 'weight': 300}).is_valid())
        self.assertTrue(ProductOptionsForm({'quantity': 1, 'grind': 'french-press', 'weight': 750}).is_valid())
