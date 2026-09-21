# views.py
from django.shortcuts import render, get_object_or_404
from .models import Category, Product

def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category).order_by('name')
    return render(request, 'products/products.html', {'category': category, 'products': products})
