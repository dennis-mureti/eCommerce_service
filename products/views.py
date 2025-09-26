"""
Views for product management API.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, F
from django.shortcuts import get_object_or_404
from customers.permissions import IsAdminOrReadOnly
from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer, CategoryTreeSerializer, ProductListSerializer,
    ProductDetailSerializer, ProductCreateUpdateSerializer,
    ProductInventorySerializer, ProductPricingSerializer,
    BulkPriceUpdateSerializer, ProductSearchSerializer, ProductImageSerializer
)
from .filters import ProductFilter
import logging

logger = logging.getLogger(__name__)


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List all categories or create a new category.
    """
    queryset = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_serializer_context(self):
        """
        Add context for including children.
        """
        context = super().get_serializer_context()
        context['include_children'] = self.request.query_params.get('include_children', 'false').lower() == 'true'
        return context
    
    def get_queryset(self):
        """
        Filter categories based on query parameters.
        """
        queryset = super().get_queryset()
        
        # Filter by parent category
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        return queryset


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a category.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    
    def perform_destroy(self, instance):
        """
        Soft delete by setting is_active to False.
        """
        if instance.products.exists():
            # Don't delete categories with products
            instance.is_active = False
            instance.save()
        else:
            instance.delete()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def category_tree(request):
    """
    Get hierarchical category tree.
    """
    root_categories = Category.objects.filter(
        parent__isnull=True,
        is_active=True
    ).order_by('sort_order', 'name')
    
    serializer = CategoryTreeSerializer(root_categories, many=True)
    return Response({
        'categories': serializer.data
    })


class ProductListCreateView(generics.ListCreateAPIView):
    """
    List all products or create a new product.
    """
    queryset = Product.objects.filter(is_active=True).select_related('category')
    permission_classes = [IsAdminOrReadOnly]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        """
        Filter products based on search parameters.
        """
        queryset = super().get_queryset()
        
        # Apply search filters
        search_serializer = ProductSearchSerializer(data=self.request.query_params)
        if search_serializer.is_valid():
            data = search_serializer.validated_data
            
            # Text search
            if data.get('q'):
                query = data['q']
                queryset = queryset.filter(
                    Q(name__icontains=query) |
                    Q(description__icontains=query) |
                    Q(sku__icontains=query)
                )
            
            # Category filter
            if data.get('category'):
                queryset = queryset.filter(category_id=data['category'])
            
            # Price range filter
            if data.get('min_price'):
                queryset = queryset.filter(price__gte=data['min_price'])
            if data.get('max_price'):
                queryset = queryset.filter(price__lte=data['max_price'])
            
            # Stock filter
            if data.get('in_stock') is not None:
                if data['in_stock']:
                    queryset = queryset.filter(stock_quantity__gt=0)
                else:
                    queryset = queryset.filter(stock_quantity=0)
            
            # Featured filter
            if data.get('is_featured') is not None:
                queryset = queryset.filter(is_featured=data['is_featured'])
            
            # Ordering
            ordering = data.get('ordering', '-created_at')
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Log product creation.
        """
        product = serializer.save()
        logger.info(f"Product created: {product.name} ({product.sku})")


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product.
    """
    queryset = Product.objects.all().select_related('category').prefetch_related('images')
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'sku'
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def perform_destroy(self, instance):
        """
        Soft delete by setting is_active to False.
        """
        instance.is_active = False
        instance.save()
        logger.info(f"Product deactivated: {instance.name} ({instance.sku})")


class ProductInventoryView(generics.ListAPIView):
    """
    View for inventory management.
    """
    queryset = Product.objects.filter(is_active=True).order_by('name')
    serializer_class = ProductInventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter products based on inventory status.
        """
        queryset = super().get_queryset()
        
        # Filter by stock status
        stock_status = self.request.query_params.get('stock_status')
        if stock_status == 'low':
            queryset = queryset.filter(stock_quantity__lte=F('low_stock_threshold'))
        elif stock_status == 'out':
            queryset = queryset.filter(stock_quantity=0)
        elif stock_status == 'in':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_inventory(request, sku):
    """
    Update product inventory.
    """
    product = get_object_or_404(Product, sku=sku, is_active=True)
    
    action = request.data.get('action')
    quantity = request.data.get('quantity', 0)
    
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return Response({
                'error': 'Quantity must be positive'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'error': 'Invalid quantity'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if action == 'add':
        product.increase_stock(quantity)
        message = f"Added {quantity} units to inventory"
    elif action == 'remove':
        if product.reduce_stock(quantity):
            message = f"Removed {quantity} units from inventory"
        else:
            return Response({
                'error': 'Insufficient stock'
            }, status=status.HTTP_400_BAD_REQUEST)
    elif action == 'set':
        product.stock_quantity = quantity
        product.save(update_fields=['stock_quantity'])
        message = f"Set inventory to {quantity} units"
    else:
        return Response({
            'error': 'Invalid action. Use add, remove, or set'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"Inventory updated for {product.sku}: {message}")
    
    serializer = ProductInventorySerializer(product)
    return Response({
        'product': serializer.data,
        'message': message
    })


class ProductPricingView(generics.ListAPIView):
    """
    View for pricing management.
    """
    queryset = Product.objects.filter(is_active=True).order_by('name')
    serializer_class = ProductPricingSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_price_update(request):
    """
    Bulk update product prices.
    """
    serializer = BulkPriceUpdateSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        product_ids = data['product_ids']
        
        # Get products
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        if len(products) != len(product_ids):
            return Response({
                'error': 'Some products not found or inactive'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_products = []
        
        for product in products:
            old_price = product.price
            
            if data.get('price_adjustment'):
                product.price += data['price_adjustment']
            elif data.get('percentage_adjustment'):
                adjustment = (data['percentage_adjustment'] / 100) * product.price
                product.price += adjustment
            
            # Ensure price is not negative
            if product.price < 0:
                product.price = 0
            
            product.save(update_fields=['price'])
            
            updated_products.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'old_price': str(old_price),
                'new_price': str(product.price)
            })
        
        logger.info(f"Bulk price update completed for {len(updated_products)} products")
        
        return Response({
            'message': f'Updated prices for {len(updated_products)} products',
            'products': updated_products
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductImageListCreateView(generics.ListCreateAPIView):
    """
    List or create product images.
    """
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Get images for specific product.
        """
        product_sku = self.kwargs['sku']
        product = get_object_or_404(Product, sku=product_sku)
        return product.images.all().order_by('sort_order', 'created_at')
    
    def perform_create(self, serializer):
        """
        Associate image with product.
        """
        product_sku = self.kwargs['sku']
        product = get_object_or_404(Product, sku=product_sku)
        serializer.save(product=product)


class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product image.
    """
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Get images for specific product.
        """
        product_sku = self.kwargs['sku']
        product = get_object_or_404(Product, sku=product_sku)
        return product.images.all()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_products(request):
    """
    Get featured products.
    """
    products = Product.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('category').order_by('-created_at')[:12]
    
    serializer = ProductListSerializer(products, many=True, context={'request': request})
    return Response({
        'products': serializer.data,
        'count': len(products)
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_recommendations(request, sku):
    """
    Get product recommendations based on category.
    """
    product = get_object_or_404(Product, sku=sku, is_active=True)
    
    # Get products from same category, excluding current product
    recommendations = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('-created_at')[:6]
    
    serializer = ProductListSerializer(recommendations, many=True, context={'request': request})
    return Response({
        'recommendations': serializer.data,
        'count': len(recommendations)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def low_stock_alert(request):
    """
    Get products with low stock levels.
    """
    low_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=F('low_stock_threshold')
    ).order_by('stock_quantity')
    
    serializer = ProductInventorySerializer(low_stock_products, many=True)
    return Response({
        'low_stock_products': serializer.data,
        'count': len(low_stock_products)
    })
