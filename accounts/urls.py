from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.decorators.http import require_POST

from accounts.views import CustomLoginView, profile, registerPage, resend_verification, verify_email


urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', registerPage, name='register'),
    # POST only, so a link or image on another page cannot log the user out.
    path('logout/', require_POST(auth_views.LogoutView.as_view(next_page='/')), name='logout'),
    path('profile/', profile, name='profile'),
    path('verify/resend/', resend_verification, name='resend_verification'),
    path('verify/<str:token>/', verify_email, name='verify_email'),

    # Password reset using Django's built-in views; emails are printed to the console in development.
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.txt',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
