# views.py
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .forms import get_add_to_cart_form
from .models import Category, Product

PRODUCTS_PER_PAGE = 6
SORT_OPTIONS = {
    'name': 'name',
    'price_low': 'price',
    'price_high': '-price',
}


# Sort and paginate a product queryset using the sort and page query parameters.
def _sorted_page(request, products):
    sort = request.GET.get('sort', 'name')
    products = products.order_by(SORT_OPTIONS.get(sort, 'name'))
    page = Paginator(products, PRODUCTS_PER_PAGE).get_page(request.GET.get('page'))
    return page, sort


# Show the available products that belong to one selected category.
def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, is_available=True).select_related('category')
    page, sort = _sorted_page(request, products)
    return render(request, 'products/products.html', {
        'title': category.name,
        'category': category,
        'page_obj': page,
        'sort': sort,
    })


# Search available products by name or description across all categories.
def product_search(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_available=True).select_related('category')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    else:
        products = products.none()

    page, sort = _sorted_page(request, products)
    return render(request, 'products/products.html', {
        'title': f'Search results for "{query}"' if query else 'Search',
        'query': query,
        'page_obj': page,
        'sort': sort,
    })


# Show one product with its add-to-cart options.
def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category'), id=product_id, is_available=True)
    return render(request, 'products/detail.html', {
        'product': product,
        'form': get_add_to_cart_form(product),
    })
