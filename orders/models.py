from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F

from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = 'cod', 'Cash on delivery'
        ONLINE = 'online', 'Online payment (demo)'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'
        REFUNDED = 'refunded', 'Refunded'

    # The statuses each status is allowed to move to next.
    ALLOWED_TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.COMPLETED, Status.CANCELLED},
        Status.COMPLETED: set(),
        Status.CANCELLED: set(),
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.TextField()
    phone = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH_ON_DELIVERY)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    # Return a short label for orders in Django admin and templates.
    def __str__(self):
        return f'Order #{self.id} by {self.user.username}'

    # Check whether the order may move from its current status to new_status.
    def can_change_status(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS[self.status]

    # Customers may only cancel an order that the shop has not confirmed yet.
    @property
    def can_be_cancelled_by_user(self):
        return self.status == self.Status.PENDING

    # Online orders need payment before the shop processes them.
    @property
    def needs_payment(self):
        return (
            self.payment_method == self.PaymentMethod.ONLINE
            and self.payment_status == self.PaymentStatus.UNPAID
            and self.status == self.Status.PENDING
        )

    # Move the order to a new status; cancelling returns stock and refunds a paid order.
    def change_status(self, new_status):
        if not self.can_change_status(new_status):
            raise ValueError(f'Cannot change order from {self.status} to {new_status}.')

        with transaction.atomic():
            if new_status == self.Status.CANCELLED:
                for item in self.items.all():
                    Product.objects.filter(id=item.product_id).update(stock=F('stock') + item.quantity)
                if self.payment_status == self.PaymentStatus.PAID:
                    self.payment_status = self.PaymentStatus.REFUNDED

            self.status = new_status
            self.save(update_fields=['status', 'payment_status', 'updated_at'])

    # Record a successful demo payment and confirm the order.
    def mark_paid(self):
        self.payment_status = self.PaymentStatus.PAID
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status', 'payment_status', 'updated_at'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    grind = models.CharField(max_length=30, blank=True, default='')
    weight = models.PositiveIntegerField(null=True, blank=True)

    # Return the saved subtotal using the price when the order was placed.
    def get_cost(self):
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity

    # Return a descriptive label for an individual order item.
    def __str__(self):
        return f'{self.quantity} x {self.product_name}'
