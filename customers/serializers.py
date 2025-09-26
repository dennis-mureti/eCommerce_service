"""
Serializers for customer authentication and management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Customer


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number', 'date_of_birth',
            'address', 'sms_notifications_enabled', 'email_notifications_enabled'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        """
        Create new customer with hashed password.
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        customer = Customer.objects.create_user(
            password=password,
            **validated_data
        )
        return customer


class CustomerLoginSerializer(serializers.Serializer):
    """
    Serializer for customer login.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """
        Validate customer credentials.
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            customer = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not customer:
                raise serializers.ValidationError('Invalid credentials')
            
            if not customer.is_active:
                raise serializers.ValidationError('Account is disabled')
            
            attrs['customer'] = customer
            return attrs
        
        raise serializers.ValidationError('Must include username and password')


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for customer profile management.
    """
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'date_of_birth', 'address',
            'sms_notifications_enabled', 'email_notifications_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """
        Validate old password.
        """
        customer = self.context['request'].user
        if not customer.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def validate(self, attrs):
        """
        Validate new password confirmation.
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        """
        Save new password.
        """
        customer = self.context['request'].user
        customer.set_password(self.validated_data['new_password'])
        customer.save()
        return customer


class OIDCTokenSerializer(serializers.Serializer):
    """
    Serializer for OpenID Connect token authentication.
    """
    id_token = serializers.CharField()
    
    def validate_id_token(self, value):
        """
        Validate the OpenID Connect ID token.
        """
        # Token validation is handled by the authentication backend
        return value
