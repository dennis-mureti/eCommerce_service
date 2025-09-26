"""
Admin configuration for product models.
"""
from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """
    Inline admin for product images.
    """
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Category model.
    """
    list_display = ('name', 'parent', 'level', 'is_active', 'sort_order', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['parent__name', 'sort_order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'parent')
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def level(self, obj):
        """Display category level."""
        return obj.level
    level.short_description = 'Level'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model.
    """
    list_display = ('name', 'sku', 'category', 'price', 'stock_quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'sku', 'description')
    ordering = ['-created_at']
    inlines = [ProductImageInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'sku', 'description', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
        ('Physical Attributes', {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('category')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductImage model.
    """
    list_display = ('product', 'alt_text', 'is_primary', 'sort_order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    ordering = ['product', 'sort_order']
