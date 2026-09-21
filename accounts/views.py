from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView

from accounts.forms import CustomAuthenticationForm,SignupForm
#from django.contrib.auth.forms import UserCreationForm

from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User



class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm

    def get_success_url(self):
        return reverse_lazy('home')

    def form_valid(self, form):
        print("Authentication successful for user:", form.get_user())
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Authentication failed. Invalid credentials.")
        return super().form_invalid(form)



def registerPage(request):
    form = SignupForm()

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                form.add_error('email', 'This email is already registered.')
                return render(request, 'accounts/register.html', {'form': form})

            user = form.save(commit=False)
            user.username = email
            user.save()

            messages.success(request, "Account registered for "+ email )
            return redirect('login')
        
    context = {'form':form}
    return render(request, 'accounts/register.html',context)