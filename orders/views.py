import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Profile
from cart.cart import Cart

from .forms import CheckoutForm
from .models import Order
from .services import OutOfStockError, place_order, remember_delivery_details

logger = logging.getLogger(__name__)


# Create an order from the logged-in user's current cart.
@login_required
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)

    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:detail')

    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, form.save(commit=False), cart_items)
            except OutOfStockError as error:
                messages.error(request, f'{error} Please update your cart.')
                return redirect('cart:detail')

            cart.clear()
            remember_delivery_details(profile, order)

            if order.needs_payment:
                return redirect('orders:pay', order_id=order.id)

            messages.success(request, 'Your order has been placed successfully.')
            return redirect('orders:success', order_id=order.id)
    else:
        form = CheckoutForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': profile.phone,
            'address': profile.address,
        })

    return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})


# Show the confirmation page only to the user who placed the order.
@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/success.html', {'order': order})


# List the logged-in user's orders, newest first.
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/order_list.html', {'orders': orders})


# Show one of the logged-in user's orders with its items.
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


# Let a customer cancel their own order while it is still pending.
@login_required
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.can_be_cancelled_by_user:
        order.change_status(Order.Status.CANCELLED)
        logger.info('Order #%s cancelled by %s', order.id, request.user.username)
        messages.success(request, f'Order #{order.id} has been cancelled.')
    else:
        messages.error(request, 'This order can no longer be cancelled.')

    return redirect('orders:detail', order_id=order.id)


# Demo payment page: the Pay button marks the order as paid without a real payment gateway.
@login_required
def order_pay(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.needs_payment:
        messages.info(request, 'This order does not need payment.')
        return redirect('orders:detail', order_id=order.id)

    if request.method == 'POST':
        order.mark_paid()
        logger.info('Order #%s paid by %s', order.id, request.user.username)
        messages.success(request, 'Payment successful. Your order is confirmed.')
        return redirect('orders:success', order_id=order.id)

    return render(request, 'orders/pay.html', {'order': order})
