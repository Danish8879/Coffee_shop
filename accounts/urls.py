from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LogoutView

from accounts.views import CustomLoginView,registerPage


urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    #path('register/', RegisterView.as_view(), name='register'),
    path('register/', registerPage, name='register'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
] 