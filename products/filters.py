"""
Filters for product API.
"""
import django_filters
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """
    Filter set for product queries.
    """
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all())
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'is_active', 'is_featured']
    
    def filter_in_stock(self, queryset, name, value):
        """
        Filter products by stock availability.
        """
        if value:
            return queryset.filter(stock_quantity__gt=0)
        else:
            return queryset.filter(stock_quantity=0)
