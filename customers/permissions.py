"""
Custom permissions for customer operations.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj == request.user


class IsCustomer(permissions.BasePermission):
    """
    Permission to check if user is a customer (not staff/admin).
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            not request.user.is_staff
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read access to everyone, write access to admin only.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )
