from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cart.cart import Cart

from .forms import CheckoutForm
from .models import Order, OrderItem


# Create an order from the logged-in user's current cart.
@login_required
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)

    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.total_amount = cart.get_total_price()
                order.save()

                for item in cart_items:
                    product = item['product']
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=product.price,
                        quantity=item['quantity'],
                    )

                cart.clear()

            messages.success(request, 'Your order has been placed successfully.')
            return redirect('orders:success', order_id=order.id)
    else:
        form = CheckoutForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})


# Show the confirmation page only to the user who placed the order.
@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/success.html', {'order': order})
