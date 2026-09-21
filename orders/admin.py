from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity', 'get_cost')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'user__username', 'email', 'phone')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    inlines = (OrderItemInline,)
