"""
URL patterns for product management API.
"""
from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView, category_tree,
    ProductListCreateView, ProductDetailView, ProductInventoryView,
    ProductPricingView, ProductImageListCreateView, ProductImageDetailView,
    featured_products, product_recommendations, low_stock_alert,
    update_inventory, bulk_price_update
)

urlpatterns = [
    # Category endpoints
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/tree/', category_tree, name='category-tree'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Product endpoints
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('featured/', featured_products, name='featured-products'),
    path('<str:sku>/', ProductDetailView.as_view(), name='product-detail'),
    path('<str:sku>/recommendations/', product_recommendations, name='product-recommendations'),
    
    # Product images
    path('<str:sku>/images/', ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('<str:sku>/images/<int:pk>/', ProductImageDetailView.as_view(), name='product-image-detail'),
    
    # Inventory management
    path('inventory/', ProductInventoryView.as_view(), name='product-inventory'),
    path('inventory/low-stock/', low_stock_alert, name='low-stock-alert'),
    path('inventory/<str:sku>/update/', update_inventory, name='update-inventory'),
    
    # Pricing management
    path('pricing/', ProductPricingView.as_view(), name='product-pricing'),
    path('pricing/bulk-update/', bulk_price_update, name='bulk-price-update'),
]
