"""
Serializers for order management API.
"""
from rest_framework import serializers
from decimal import Decimal
from django.db import transaction
from .models import Order, OrderItem, OrderStatusHistory
from products.models import Product
from products.serializers import ProductListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items.
    """
    product_name = serializers.ReadOnlyField()
    product_sku = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    product_details = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'quantity',
            'unit_price', 'total_price', 'product_details', 'created_at'
        ]
        read_only_fields = ['id', 'unit_price', 'created_at']
    
    def get_product_details(self, obj):
        """
        Get basic product details for the order item.
        """
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.name,
                'sku': obj.product.sku,
                'current_price': str(obj.product.price),
                'is_active': obj.product.is_active
            }
        return None


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating order items.
    """
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']
    
    def validate_product(self, value):
        """
        Validate product is active and available.
        """
        if not value.is_active:
            raise serializers.ValidationError("Product is not available.")
        return value
    
    def validate_quantity(self, value):
        """
        Validate quantity is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive.")
        return value
    
    def validate(self, attrs):
        """
        Validate stock availability.
        """
        product = attrs['product']
        quantity = attrs['quantity']
        
        if product.stock_quantity < quantity:
            raise serializers.ValidationError(
                f"Insufficient stock. Only {product.stock_quantity} units available."
            )
        
        return attrs


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for order status history.
    """
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'from_status', 'to_status', 'notes',
            'changed_by', 'changed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderListSerializer(serializers.ModelSerializer):
    """
    Serializer for order list view.
    """
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    total_items = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'status',
            'payment_status', 'total_amount', 'total_items', 'created_at'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed order view.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    total_items = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_email',
            'status', 'payment_status', 'subtotal', 'tax_amount', 'shipping_amount',
            'total_amount', 'shipping_address', 'shipping_phone', 'customer_notes',
            'admin_notes', 'total_items', 'items', 'status_history',
            'created_at', 'updated_at', 'shipped_at', 'delivered_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer', 'subtotal', 'total_amount',
            'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating orders.
    """
    items = OrderItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'shipping_address', 'shipping_phone', 'customer_notes',
            'tax_amount', 'shipping_amount', 'items'
        ]
    
    def validate_items(self, value):
        """
        Validate order items.
        """
        if not value:
            raise serializers.ValidationError("Order must contain at least one item.")
        
        # Check for duplicate products
        product_ids = [item['product'].id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate products in order.")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create order with items.
        """
        items_data = validated_data.pop('items')
        customer = self.context['request'].user
        
        # Calculate subtotal
        subtotal = Decimal('0.00')
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            subtotal += product.price * quantity
        
        # Create order
        order = Order.objects.create(
            customer=customer,
            subtotal=subtotal,
            total_amount=subtotal + validated_data.get('tax_amount', Decimal('0.00')) + 
                        validated_data.get('shipping_amount', Decimal('0.00')),
            **validated_data
        )
        
        # Create order items and reduce stock
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )
            
            # Reduce stock
            product.reduce_stock(quantity)
        
        # Create initial status history
        OrderStatusHistory.objects.create(
            order=order,
            to_status='pending',
            notes='Order created',
            changed_by=customer
        )
        
        return order


class OrderUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating orders (admin only).
    """
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'tax_amount', 'shipping_amount',
            'shipping_address', 'shipping_phone', 'admin_notes'
        ]
    
    def update(self, instance, validated_data):
        """
        Update order and track status changes.
        """
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Update order
        order = super().update(instance, validated_data)
        
        # Track status change
        if old_status != new_status:
            OrderStatusHistory.objects.create(
                order=order,
                from_status=old_status,
                to_status=new_status,
                notes=f"Status changed from {old_status} to {new_status}",
                changed_by=self.context['request'].user
            )
            
            # Update timestamps
            if new_status == 'shipped' and not order.shipped_at:
                order.shipped_at = timezone.now()
                order.save(update_fields=['shipped_at'])
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
                order.save(update_fields=['delivered_at'])
        
        # Recalculate total if tax or shipping changed
        if 'tax_amount' in validated_data or 'shipping_amount' in validated_data:
            order.total_amount = order.subtotal + order.tax_amount + order.shipping_amount
            order.save(update_fields=['total_amount'])
        
        return order


class CartItemSerializer(serializers.Serializer):
    """
    Serializer for cart items (session-based).
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    product = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    def get_product(self, obj):
        """
        Get product details.
        """
        try:
            product = Product.objects.get(id=obj['product_id'], is_active=True)
            return {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': str(product.price),
                'stock_quantity': product.stock_quantity,
                'is_in_stock': product.is_in_stock
            }
        except Product.DoesNotExist:
            return None
    
    def get_total_price(self, obj):
        """
        Calculate total price for cart item.
        """
        try:
            product = Product.objects.get(id=obj['product_id'], is_active=True)
            return str(product.price * obj['quantity'])
        except Product.DoesNotExist:
            return "0.00"


class CartSerializer(serializers.Serializer):
    """
    Serializer for shopping cart.
    """
    items = CartItemSerializer(many=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    
    def get_total_items(self, obj):
        """
        Get total number of items in cart.
        """
        return sum(item['quantity'] for item in obj['items'])
    
    def get_subtotal(self, obj):
        """
        Calculate cart subtotal.
        """
        total = Decimal('0.00')
        for item in obj['items']:
            try:
                product = Product.objects.get(id=item['product_id'], is_active=True)
                total += product.price * item['quantity']
            except Product.DoesNotExist:
                continue
        return str(total)


class OrderSearchSerializer(serializers.Serializer):
    """
    Serializer for order search parameters.
    """
    customer = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, required=False)
    payment_status = serializers.ChoiceField(choices=Order.PAYMENT_STATUS_CHOICES, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    min_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    ordering = serializers.ChoiceField(
        choices=[
            'created_at', '-created_at', 'total_amount', '-total_amount',
            'status', '-status', 'order_number', '-order_number'
        ],
        required=False,
        default='-created_at'
    )
