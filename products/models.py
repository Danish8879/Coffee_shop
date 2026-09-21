# models.py
from django.db import models
from decimal import Decimal

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

    # Calculate this bean's price for a selected weight in grams.
    def get_price_for_weight(self, weight_grams):
        return (self.price * Decimal(str(weight_grams)) / Decimal('250')).quantize(Decimal('0.01'))
