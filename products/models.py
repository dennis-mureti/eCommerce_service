"""
Product models for the e-commerce system with hierarchical categories.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """
    Hierarchical product categories using adjacency list model.
    """
    name = models.CharField(
        max_length=100,
        help_text="Category name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Category description"
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent category (null for root categories)"
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly category identifier"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is active"
    )
    
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Sort order within parent category"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
        unique_together = ['parent', 'slug']
    
    def __str__(self):
        return self.get_full_path()
    
    def get_full_path(self):
        """Return the full category path (e.g., 'Electronics > Phones > Smartphones')."""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name
    
    def get_ancestors(self):
        """Return all ancestor categories."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return reversed(ancestors)
    
    def get_descendants(self):
        """Return all descendant categories."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    @property
    def level(self):
        """Return the category level (0 for root categories)."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level


class Product(models.Model):
    """
    Product model with pricing and inventory management.
    """
    name = models.CharField(
        max_length=200,
        help_text="Product name"
    )
    
    description = models.TextField(
        help_text="Product description"
    )
    
    sku = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stock Keeping Unit - unique product identifier"
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        help_text="Product category"
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Product price"
    )
    
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Cost price for profit calculation"
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Current stock quantity"
    )
    
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Threshold for low stock alerts"
    )
    
    # Product attributes
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Product weight in kg"
    )
    
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        help_text="Product dimensions (L x W x H)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is active and available for sale"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this product is featured"
    )
    
    # SEO
    meta_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="SEO meta title"
    )
    
    meta_description = models.TextField(
        blank=True,
        help_text="SEO meta description"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active', 'is_featured']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        """Check if product stock is below threshold."""
        return self.stock_quantity <= self.low_stock_threshold
    
    def reduce_stock(self, quantity):
        """Reduce stock quantity by given amount."""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save(update_fields=['stock_quantity'])
            return True
        return False
    
    def increase_stock(self, quantity):
        """Increase stock quantity by given amount."""
        self.stock_quantity += quantity
        self.save(update_fields=['stock_quantity'])


class ProductImage(models.Model):
    """
    Product images with ordering support.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        help_text="Associated product"
    )
    
    image = models.ImageField(
        upload_to='products/images/',
        help_text="Product image"
    )
    
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Alternative text for accessibility"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary product image"
    )
    
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"
