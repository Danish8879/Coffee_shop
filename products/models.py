# models.py
from django.db import models
from decimal import Decimal

COFFEE_BEANS_SLUG = 'coffee-beans'


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True)

    def __str__(self):
        return self.name

    # Only coffee beans are sold with a grind and packet weight choice.
    @property
    def has_bean_options(self):
        return self.category.slug == COFFEE_BEANS_SLUG

    # Calculate the price for a selected weight in grams; products without a weight use the base price.
    def get_price_for_weight(self, weight_grams=None):
        if not weight_grams:
            return self.price
        return (self.price * Decimal(str(weight_grams)) / Decimal('250')).quantize(Decimal('0.01'))
