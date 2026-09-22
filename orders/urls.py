from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='list'),
    path('checkout/', views.checkout, name='checkout'),
    path('<int:order_id>/', views.order_detail, name='detail'),
    path('<int:order_id>/cancel/', views.order_cancel, name='cancel'),
    path('<int:order_id>/pay/', views.order_pay, name='pay'),
    path('success/<int:order_id>/', views.order_success, name='success'),
]
