# urls.py
from django.urls import path
from .views import product_list_by_category

urlpatterns = [
    path('category/<slug:category_slug>/', product_list_by_category, name='product_list_by_category'),
]
