"""
Serializers for product management API.
"""
from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model with hierarchical support.
    """
    children = serializers.SerializerMethodField()
    full_path = serializers.ReadOnlyField()
    level = serializers.ReadOnlyField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'slug', 'parent', 'is_active',
            'sort_order', 'full_path', 'level', 'children', 'product_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_children(self, obj):
        """
        Get child categories if requested.
        """
        if self.context.get('include_children', False):
            children = obj.children.filter(is_active=True).order_by('sort_order', 'name')
            return CategorySerializer(children, many=True, context=self.context).data
        return []
    
    def get_product_count(self, obj):
        """
        Get count of active products in this category.
        """
        return obj.products.filter(is_active=True).count()


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Serializer for hierarchical category tree.
    """
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'children']
    
    def get_children(self, obj):
        """
        Recursively get all child categories.
        """
        children = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return CategoryTreeSerializer(children, many=True).data


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'sort_order', 'created_at']
        read_only_fields = ['created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for product list view (minimal data).
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'price', 'category_name', 'primary_image',
            'is_active', 'is_featured', 'stock_quantity', 'is_in_stock',
            'created_at'
        ]
    
    def get_primary_image(self, obj):
        """
        Get primary product image.
        """
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed product view.
    """
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'category', 'category_id',
            'price', 'cost_price', 'stock_quantity', 'low_stock_threshold',
            'weight', 'dimensions', 'is_active', 'is_featured',
            'meta_title', 'meta_description', 'images',
            'is_in_stock', 'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_sku(self, value):
        """
        Validate SKU uniqueness.
        """
        if self.instance:
            # Update case - exclude current instance
            if Product.objects.exclude(pk=self.instance.pk).filter(sku=value).exists():
                raise serializers.ValidationError("Product with this SKU already exists.")
        else:
            # Create case
            if Product.objects.filter(sku=value).exists():
                raise serializers.ValidationError("Product with this SKU already exists.")
        return value
    
    def validate_category_id(self, value):
        """
        Validate category exists and is active.
        """
        try:
            category = Category.objects.get(pk=value)
            if not category.is_active:
                raise serializers.ValidationError("Cannot assign product to inactive category.")
            return value
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating products.
    """
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'sku', 'category', 'price', 'cost_price',
            'stock_quantity', 'low_stock_threshold', 'weight', 'dimensions',
            'is_active', 'is_featured', 'meta_title', 'meta_description'
        ]
    
    def validate_sku(self, value):
        """
        Validate SKU uniqueness.
        """
        if self.instance:
            if Product.objects.exclude(pk=self.instance.pk).filter(sku=value).exists():
                raise serializers.ValidationError("Product with this SKU already exists.")
        else:
            if Product.objects.filter(sku=value).exists():
                raise serializers.ValidationError("Product with this SKU already exists.")
        return value


class ProductInventorySerializer(serializers.ModelSerializer):
    """
    Serializer for inventory management.
    """
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'stock_quantity', 'low_stock_threshold', 'is_in_stock', 'is_low_stock']
        read_only_fields = ['id', 'sku', 'name', 'is_in_stock', 'is_low_stock']


class ProductPricingSerializer(serializers.ModelSerializer):
    """
    Serializer for pricing management.
    """
    profit_margin = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'price', 'cost_price', 'profit_margin']
        read_only_fields = ['id', 'sku', 'name', 'profit_margin']
    
    def get_profit_margin(self, obj):
        """
        Calculate profit margin percentage.
        """
        if obj.cost_price and obj.cost_price > 0:
            margin = ((obj.price - obj.cost_price) / obj.cost_price) * 100
            return round(margin, 2)
        return None


class BulkPriceUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk price updates.
    """
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    price_adjustment = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount to add/subtract from current price"
    )
    percentage_adjustment = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Percentage to increase/decrease price by"
    )
    
    def validate(self, attrs):
        """
        Validate that either price_adjustment or percentage_adjustment is provided.
        """
        if not attrs.get('price_adjustment') and not attrs.get('percentage_adjustment'):
            raise serializers.ValidationError(
                "Either price_adjustment or percentage_adjustment must be provided."
            )
        
        if attrs.get('price_adjustment') and attrs.get('percentage_adjustment'):
            raise serializers.ValidationError(
                "Provide either price_adjustment or percentage_adjustment, not both."
            )
        
        return attrs


class ProductSearchSerializer(serializers.Serializer):
    """
    Serializer for product search parameters.
    """
    q = serializers.CharField(required=False, help_text="Search query")
    category = serializers.IntegerField(required=False, help_text="Category ID")
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    in_stock = serializers.BooleanField(required=False, help_text="Filter by stock availability")
    is_featured = serializers.BooleanField(required=False, help_text="Filter featured products")
    ordering = serializers.ChoiceField(
        choices=[
            'name', '-name', 'price', '-price', 'created_at', '-created_at',
            'stock_quantity', '-stock_quantity'
        ],
        required=False,
        default='-created_at'
    )
