"""
Admin configuration for order models.
"""
from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    """
    Inline admin for order items.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)
    fields = ('product', 'quantity', 'unit_price', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    """
    Inline admin for order status history.
    """
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('from_status', 'to_status', 'notes', 'changed_by', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin interface for Order model.
    """
    list_display = ('order_number', 'customer', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'updated_at')
    search_fields = ('order_number', 'customer__username', 'customer__email')
    ordering = ['-created_at']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'total_items')
    
    fieldsets = (
        (None, {
            'fields': ('order_number', 'customer', 'status', 'payment_status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'shipping_amount', 'total_amount')
        }),
        ('Shipping', {
            'fields': ('shipping_address', 'shipping_phone')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('customer')
    
    def total_items(self, obj):
        """Display total items in order."""
        return obj.total_items
    total_items.short_description = 'Total Items'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Admin interface for OrderItem model.
    """
    list_display = ('order', 'product_name', 'quantity', 'unit_price', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_number', 'product_name', 'product_sku')
    ordering = ['-created_at']
    readonly_fields = ('total_price',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order', 'product')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for OrderStatusHistory model.
    """
    list_display = ('order', 'from_status', 'to_status', 'changed_by', 'created_at')
    list_filter = ('from_status', 'to_status', 'created_at')
    search_fields = ('order__order_number', 'notes')
    ordering = ['-created_at']
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order', 'changed_by')
