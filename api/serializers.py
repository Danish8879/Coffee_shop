from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import Profile
from orders.forms import validate_phone
from orders.models import Order, OrderItem
from orders.services import OutOfStockError, place_order, remember_delivery_details
from products.forms import GRIND_CHOICES, MAX_ORDER_QUANTITY, WEIGHT_CHOICES
from products.models import Category, Product


# ---------- Products ----------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    has_bean_options = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'image', 'category', 'stock', 'in_stock', 'has_bean_options')


# ---------- Accounts ----------

class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=200)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    # Emails are the username, so they are stored in lower case and must be unique.
    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('This email is already registered.')
        return email

    # Apply the same password rules as the website signup form.
    def validate(self, data):
        user = User(username=data['email'], email=data['email'], first_name=data['first_name'], last_name=data['last_name'])
        try:
            validate_password(data['password'], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})
        return data

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    # Look the user up ignoring email capitalisation, then check the password.
    def validate(self, data):
        match = User.objects.filter(username__iexact=data['email'].strip()).first()
        user = authenticate(
            request=self.context.get('request'),
            username=match.username if match else data['email'],
            password=data['password'],
        )
        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        data['user'] = user
        return data


class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', max_length=150)
    last_name = serializers.CharField(source='user.last_name', max_length=150)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'is_email_verified')
        read_only_fields = ('is_email_verified',)

    # Phone is optional on the profile, but must look like a real number when given.
    def validate_phone(self, value):
        value = value.strip()
        if not value:
            return value
        try:
            return validate_phone(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

    # Save the name on the User and the delivery details on the Profile.
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            for field, value in user_data.items():
                setattr(instance.user, field, value)
            instance.user.save(update_fields=list(user_data))
        return super().update(instance, validated_data)


# ---------- Orders ----------

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(source='get_cost', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('product', 'product_name', 'price', 'quantity', 'grind', 'weight', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'status_display', 'payment_method', 'payment_status', 'total_amount',
            'first_name', 'last_name', 'email', 'address', 'phone', 'items', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class OrderLineInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_available=True).select_related('category'))
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_ORDER_QUANTITY)
    grind = serializers.ChoiceField(choices=GRIND_CHOICES, required=False)
    weight = serializers.ChoiceField(choices=WEIGHT_CHOICES, required=False)

    # Coffee beans need a grind and weight; other products must not have them.
    def validate(self, data):
        product = data['product']
        if product.has_bean_options:
            if 'grind' not in data or 'weight' not in data:
                raise serializers.ValidationError(f'{product.name} needs a grind and a weight.')
            data['weight'] = int(data['weight'])
        else:
            if 'grind' in data or 'weight' in data:
                raise serializers.ValidationError(f'{product.name} has no grind or weight options.')
            data['grind'], data['weight'] = '', None
        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderLineInputSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ('first_name', 'last_name', 'email', 'address', 'phone', 'payment_method', 'items')

    def validate_phone(self, value):
        try:
            return validate_phone(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('An order needs at least one item.')
        return value

    # Place the order through the same service the website checkout uses.
    def create(self, validated_data):
        lines = validated_data.pop('items')
        user = self.context['request'].user
        try:
            order = place_order(user, Order(**validated_data), lines)
        except OutOfStockError as error:
            raise serializers.ValidationError({'items': [str(error)]})

        profile, _ = Profile.objects.get_or_create(user=user)
        remember_delivery_details(profile, order)
        return order

    # Respond with the full order, including items and totals.
    def to_representation(self, instance):
        return OrderSerializer(instance, context=self.context).data


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
