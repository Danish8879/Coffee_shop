import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from accounts.emails import send_verification_email
from accounts.forms import CustomAuthenticationForm, ProfileForm, SignupForm, UserNameForm
from accounts.models import Profile

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy('home')

    def form_valid(self, form):
        logger.info('User %s logged in', form.get_user().username)
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning('Failed login attempt for %s', form.data.get('username', ''))
        return super().form_invalid(form)


# Create a new account and send the email verification link.
def registerPage(request):
    form = SignupForm()

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = form.save()
            send_verification_email(request, user)
            logger.info('New account registered: %s', email)

            messages.success(request, "Account registered for " + email + ". Check your email to verify your address.")
            return redirect('login')

    context = {'form':form}
    return render(request, 'accounts/register.html',context)


# Show and edit the logged-in user's name and delivery details.
@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserNameForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        user_form = UserNameForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'recent_orders': request.user.orders.all()[:5],
    })


# Mark the email address as verified when the user opens the link from their email.
def verify_email(request, token):
    profile = get_object_or_404(Profile, email_token=token)
    profile.is_email_verified = True
    profile.email_token = None
    profile.save(update_fields=['is_email_verified', 'email_token', 'updated_at'])

    messages.success(request, 'Your email address has been verified.')
    return redirect('profile' if request.user.is_authenticated else 'login')


# Send a new verification email to the logged-in user.
@login_required
@require_POST
def resend_verification(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.is_email_verified:
        messages.info(request, 'Your email address is already verified.')
    elif not request.user.email:
        messages.error(request, 'Your account has no email address.')
    else:
        send_verification_email(request, request.user)
        messages.success(request, f'A verification link has been sent to {request.user.email}.')
    return redirect('profile')
