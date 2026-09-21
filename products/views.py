# views.py
from django.shortcuts import render, get_object_or_404

from .forms import ProductOptionsForm
from .models import Category, Product


# Show the products that belong to one selected category.
def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category).order_by('name')
    return render(request, 'products/products.html', {'category': category, 'products': products})


# Show the grind and weight choices for one coffee bean product.
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, category__slug='coffee-beans')
    return render(request, 'products/detail.html', {
        'product': product,
        'form': ProductOptionsForm(),
    })
