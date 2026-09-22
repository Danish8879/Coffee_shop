from django import forms

from .models import Order


# Reject phone values that do not contain a practical number of digits.
def validate_phone(phone):
    phone = phone.strip()
    if sum(character.isdigit() for character in phone) < 7:
        raise forms.ValidationError('Enter a valid phone number.')
    return phone


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('first_name', 'last_name', 'email', 'address', 'phone', 'payment_method')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'payment_method': forms.RadioSelect,
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data['phone'])
