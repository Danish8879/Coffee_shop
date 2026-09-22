from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.forms import get_add_to_cart_form
from products.models import Product

from .cart import Cart


# Show all products and totals currently stored in the visitor's cart.
def cart_detail(request):
    return render(request, 'cart/detail.html', {'cart': Cart(request)})


# Add a selected product to the cart and return to the cart page.
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category'), id=product_id)
    form = get_add_to_cart_form(product, request.POST)

    if not form.is_valid():
        messages.error(request, 'Please choose valid options and a quantity between 1 and 20.')
        return redirect('product_detail', product_id=product.id)

    Cart(request).add(
        product,
        quantity=form.cleaned_data['quantity'],
        grind=form.cleaned_data.get('grind', ''),
        weight=form.cleaned_data.get('weight'),
    )
    messages.success(request, f'{product.name} was added to your cart.')
    return redirect('cart:detail')


# Update the quantity of one cart line.
@require_POST
def cart_update(request, line_id):
    try:
        Cart(request).update_quantity(line_id, request.POST.get('quantity', 1))
        messages.success(request, 'Cart quantity updated.')
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a valid quantity.')

    return redirect('cart:detail')


# Remove one line from the cart.
@require_POST
def cart_remove(request, line_id):
    Cart(request).remove(line_id)
    messages.success(request, 'Item removed from your cart.')
    return redirect('cart:detail')
