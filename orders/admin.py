from django.contrib import admin, messages

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity', 'grind', 'weight', 'get_cost')
    can_delete = False

    # Order items are created at checkout only, never added by hand in admin.
    def has_add_permission(self, request, obj=None):
        return False


# Build an admin action that moves the selected orders to one status, skipping invalid moves.
def make_status_action(new_status, label):
    def action(modeladmin, request, queryset):
        changed, skipped = 0, 0
        for order in queryset:
            if order.can_change_status(new_status):
                order.change_status(new_status)
                changed += 1
            else:
                skipped += 1

        modeladmin.message_user(request, f'{changed} order(s) marked as {label.lower()}.')
        if skipped:
            modeladmin.message_user(
                request,
                f'{skipped} order(s) skipped because that status change is not allowed.',
                level=messages.WARNING,
            )

    action.__name__ = f'mark_{new_status}'
    action.short_description = f'Mark selected orders as {label.lower()}'
    return action


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'payment_method', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_status', 'created_at')
    search_fields = ('id', 'user__username', 'email', 'phone')
    # Status is changed only through the actions below so the allowed order flow is always followed.
    readonly_fields = ('status', 'payment_method', 'payment_status', 'total_amount', 'created_at', 'updated_at')
    inlines = (OrderItemInline,)
    actions = [
        make_status_action(Order.Status.CONFIRMED, 'Confirmed'),
        make_status_action(Order.Status.COMPLETED, 'Completed'),
        make_status_action(Order.Status.CANCELLED, 'Cancelled'),
    ]
