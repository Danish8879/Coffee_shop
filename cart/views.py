from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .cart import Cart


# Show all products and totals currently stored in the visitor's cart.
def cart_detail(request):
    return render(request, 'cart/detail.html', {'cart': Cart(request)})


# Add a selected product to the cart and return to the cart page.
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = request.POST.get('quantity', 1)

    try:
        Cart(request).add(product, quantity=quantity)
        messages.success(request, f'{product.name} was added to your cart.')
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a valid quantity.')

    return redirect('cart:detail')


# Update the selected product's quantity in the cart.
@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = request.POST.get('quantity', 1)

    try:
        Cart(request).update_quantity(product, quantity)
        messages.success(request, 'Cart quantity updated.')
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a valid quantity.')

    return redirect('cart:detail')


# Remove the selected product from the cart.
@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Cart(request).remove(product)
    messages.success(request, f'{product.name} was removed from your cart.')
    return redirect('cart:detail')
