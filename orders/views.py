"""
Views for order management API.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from customers.permissions import IsAdminOrReadOnly
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderUpdateSerializer, CartSerializer, CartItemSerializer,
    OrderSearchSerializer, OrderStatusHistorySerializer
)
import logging

logger = logging.getLogger(__name__)


class OrderListCreateView(generics.ListCreateAPIView):
    """
    List orders or create new order.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        """
        Filter orders based on user role and search parameters.
        """
        user = self.request.user
        
        # Base queryset
        if user.is_staff:
            queryset = Order.objects.all()
        else:
            queryset = Order.objects.filter(customer=user)
        
        queryset = queryset.select_related('customer').order_by('-created_at')
        
        # Apply search filters
        search_serializer = OrderSearchSerializer(data=self.request.query_params)
        if search_serializer.is_valid():
            data = search_serializer.validated_data
            
            # Customer filter (admin only)
            if data.get('customer') and user.is_staff:
                queryset = queryset.filter(customer_id=data['customer'])
            
            # Status filters
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])
            if data.get('payment_status'):
                queryset = queryset.filter(payment_status=data['payment_status'])
            
            # Date range filter
            if data.get('date_from'):
                queryset = queryset.filter(created_at__date__gte=data['date_from'])
            if data.get('date_to'):
                queryset = queryset.filter(created_at__date__lte=data['date_to'])
            
            # Amount range filter
            if data.get('min_amount'):
                queryset = queryset.filter(total_amount__gte=data['min_amount'])
            if data.get('max_amount'):
                queryset = queryset.filter(total_amount__lte=data['max_amount'])
            
            # Ordering
            ordering = data.get('ordering', '-created_at')
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Log order creation.
        """
        order = serializer.save()
        logger.info(f"Order created: {order.order_number} by {order.customer.email}")


class OrderDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update an order.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.request.method in ['PUT', 'PATCH']:
            return OrderUpdateSerializer
        return OrderDetailSerializer
    
    def get_queryset(self):
        """
        Filter orders based on user role.
        """
        user = self.request.user
        queryset = Order.objects.select_related('customer').prefetch_related(
            'items__product', 'status_history__changed_by'
        )
        
        if user.is_staff:
            return queryset
        else:
            return queryset.filter(customer=user)
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.request.method in ['PUT', 'PATCH']:
            # Only staff can update orders
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, order_number):
    """
    Cancel an order.
    """
    user = request.user
    
    # Get order
    if user.is_staff:
        order = get_object_or_404(Order, order_number=order_number)
    else:
        order = get_object_or_404(Order, order_number=order_number, customer=user)
    
    # Check if order can be cancelled
    if order.status in ['delivered', 'cancelled', 'refunded']:
        return Response({
            'error': f'Cannot cancel order with status: {order.status}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Cancel order
    old_status = order.status
    order.status = 'cancelled'
    order.save(update_fields=['status'])
    
    # Restore stock for cancelled orders
    for item in order.items.all():
        item.product.increase_stock(item.quantity)
    
    # Create status history
    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status='cancelled',
        notes='Order cancelled',
        changed_by=user
    )
    
    logger.info(f"Order cancelled: {order.order_number} by {user.email}")
    
    return Response({
        'message': 'Order cancelled successfully',
        'order_number': order.order_number,
        'status': order.status
    })


class CartView(APIView):
    """
    Shopping cart management (session-based).
    """
    permission_classes = [permissions.AllowAny]
    
    def get_cart(self, request):
        """
        Get cart from session.
        """
        return request.session.get('cart', {'items': []})
    
    def save_cart(self, request, cart):
        """
        Save cart to session.
        """
        request.session['cart'] = cart
        request.session.modified = True
    
    def get(self, request):
        """
        Get current cart contents.
        """
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def post(self, request):
        """
        Add item to cart.
        """
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid quantity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check stock
        if product.stock_quantity < quantity:
            return Response({
                'error': f'Insufficient stock. Only {product.stock_quantity} units available.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cart and add/update item
        cart = self.get_cart(request)
        
        # Check if product already in cart
        for item in cart['items']:
            if item['product_id'] == product_id:
                new_quantity = item['quantity'] + quantity
                if product.stock_quantity < new_quantity:
                    return Response({
                        'error': f'Insufficient stock. Only {product.stock_quantity} units available.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                item['quantity'] = new_quantity
                break
        else:
            # Add new item
            cart['items'].append({
                'product_id': product_id,
                'quantity': quantity
            })
        
        self.save_cart(request, cart)
        
        serializer = CartSerializer(cart)
        return Response({
            'message': 'Item added to cart',
            'cart': serializer.data
        })
    
    def put(self, request):
        """
        Update cart item quantity.
        """
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid quantity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cart
        cart = self.get_cart(request)
        
        # Update or remove item
        for i, item in enumerate(cart['items']):
            if item['product_id'] == product_id:
                if quantity == 0:
                    # Remove item
                    cart['items'].pop(i)
                    message = 'Item removed from cart'
                else:
                    # Check stock
                    if product.stock_quantity < quantity:
                        return Response({
                            'error': f'Insufficient stock. Only {product.stock_quantity} units available.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    # Update quantity
                    item['quantity'] = quantity
                    message = 'Cart updated'
                break
        else:
            return Response({
                'error': 'Item not found in cart'
            }, status=status.HTTP_404_NOT_FOUND)
        
        self.save_cart(request, cart)
        
        serializer = CartSerializer(cart)
        return Response({
            'message': message,
            'cart': serializer.data
        })
    
    def delete(self, request):
        """
        Clear cart.
        """
        request.session['cart'] = {'items': []}
        request.session.modified = True
        
        return Response({
            'message': 'Cart cleared'
        })


@api_view(['DELETE'])
@permission_classes([permissions.AllowAny])
def remove_cart_item(request, product_id):
    """
    Remove specific item from cart.
    """
    cart = request.session.get('cart', {'items': []})
    
    # Remove item
    for i, item in enumerate(cart['items']):
        if item['product_id'] == int(product_id):
            cart['items'].pop(i)
            break
    else:
        return Response({
            'error': 'Item not found in cart'
        }, status=status.HTTP_404_NOT_FOUND)
    
    request.session['cart'] = cart
    request.session.modified = True
    
    serializer = CartSerializer(cart)
    return Response({
        'message': 'Item removed from cart',
        'cart': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_analytics(request):
    """
    Get order analytics (admin only).
    """
    if not request.user.is_staff:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get date range
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = Order.objects.all()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Calculate analytics
    analytics = {
        'total_orders': queryset.count(),
        'total_revenue': queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'average_order_value': 0,
        'orders_by_status': {},
        'orders_by_payment_status': {},
        'top_customers': []
    }
    
    if analytics['total_orders'] > 0:
        analytics['average_order_value'] = analytics['total_revenue'] / analytics['total_orders']
    
    # Orders by status
    status_counts = queryset.values('status').annotate(count=Count('id'))
    for item in status_counts:
        analytics['orders_by_status'][item['status']] = item['count']
    
    # Orders by payment status
    payment_status_counts = queryset.values('payment_status').annotate(count=Count('id'))
    for item in payment_status_counts:
        analytics['orders_by_payment_status'][item['payment_status']] = item['count']
    
    # Top customers
    top_customers = queryset.values(
        'customer__id', 'customer__username', 'customer__email'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:10]
    
    analytics['top_customers'] = list(top_customers)
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def customer_order_history(request):
    """
    Get customer's order history with summary.
    """
    customer = request.user
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    
    # Calculate summary
    summary = {
        'total_orders': orders.count(),
        'total_spent': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'orders_by_status': {}
    }
    
    # Orders by status
    status_counts = orders.values('status').annotate(count=Count('id'))
    for item in status_counts:
        summary['orders_by_status'][item['status']] = item['count']
    
    # Recent orders
    recent_orders = orders[:10]
    serializer = OrderListSerializer(recent_orders, many=True)
    
    return Response({
        'summary': summary,
        'recent_orders': serializer.data
    })
