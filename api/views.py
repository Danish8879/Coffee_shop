import logging

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, generics, mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.emails import send_verification_email
from accounts.models import Profile
from orders.models import Order, OrderItem
from products.models import Category, Product

from .serializers import (
    CategorySerializer,
    LoginSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    ProductSerializer,
    ProfileSerializer,
    RegisterSerializer,
)

logger = logging.getLogger(__name__)


# ---------- Products ----------

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List product categories."""
    queryset = Category.objects.order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


@extend_schema(parameters=[OpenApiParameter('category', str, description='Filter by category slug, e.g. coffee-beans')])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """List and view available products. Supports ?search=, ?ordering=price and ?category=<slug>."""
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    ordering = ['name']

    def get_queryset(self):
        products = Product.objects.filter(is_available=True).select_related('category')
        category = self.request.query_params.get('category')
        if category:
            products = products.filter(category__slug=category)
        return products


# ---------- Accounts ----------

class RegisterView(APIView):
    """Create an account and return an API token."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: None})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(request, user)
        token = Token.objects.create(user=user)
        logger.info('New account registered through the API: %s', user.username)
        return Response({'token': token.key, 'email': user.email}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Exchange an email and password for an API token."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            logger.warning('Failed API login attempt for %s', request.data.get('email', ''))
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        logger.info('User %s logged in through the API', user.username)
        return Response({'token': token.key})


class LogoutView(APIView):
    """Delete the current API token."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(generics.RetrieveUpdateAPIView):
    """View or update the logged-in user's profile."""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = Profile.objects.select_related('user').get_or_create(user=self.request.user)
        return profile


# ---------- Orders ----------

class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Place orders and view your order history. Staff users can see every order."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # The API docs generator calls this without a logged-in user.
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()

        orders = Order.objects.prefetch_related(Prefetch('items', queryset=OrderItem.objects.order_by('id')))
        if self.request.user.is_staff:
            return orders
        return orders.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'change_status':
            return OrderStatusSerializer
        return OrderSerializer

    # Customers may only act on their own orders, even when staff can see them all.
    def _get_own_order(self):
        order = self.get_object()
        if order.user_id != self.request.user.id:
            raise PermissionDenied('You can only change your own orders.')
        return order

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel your own order while it is still pending."""
        order = self._get_own_order()
        if not order.can_be_cancelled_by_user:
            return Response({'detail': 'This order can no longer be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        order.change_status(Order.Status.CANCELLED)
        logger.info('Order #%s cancelled by %s through the API', order.id, request.user.username)
        return Response(OrderSerializer(order).data)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Demo payment for an online order: marks it paid and confirmed."""
        order = self._get_own_order()
        if not order.needs_payment:
            return Response({'detail': 'This order does not need payment.'}, status=status.HTTP_400_BAD_REQUEST)

        order.mark_paid()
        logger.info('Order #%s paid by %s through the API', order.id, request.user.username)
        return Response(OrderSerializer(order).data)

    @extend_schema(request=OrderStatusSerializer, responses=OrderSerializer)
    @action(detail=True, methods=['post'], url_path='status', permission_classes=[permissions.IsAdminUser])
    def change_status(self, request, pk=None):
        """Staff only: move an order to its next status (pending -> confirmed -> completed, or cancelled)."""
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']

        if not order.can_change_status(new_status):
            return Response(
                {'detail': f'Cannot change order from {order.status} to {new_status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.change_status(new_status)
        logger.info('Order #%s moved to %s by %s', order.id, new_status, request.user.username)
        return Response(OrderSerializer(order).data)
