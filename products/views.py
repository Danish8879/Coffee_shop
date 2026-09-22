# views.py
from django.shortcuts import render, get_object_or_404

from .forms import get_add_to_cart_form
from .models import Category, Product


# Show the products that belong to one selected category.
def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category).order_by('name')
    return render(request, 'products/products.html', {'category': category, 'products': products})


# Show one product with its add-to-cart options.
def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category'), id=product_id)
    return render(request, 'products/detail.html', {
        'product': product,
        'form': get_add_to_cart_form(product),
    })
