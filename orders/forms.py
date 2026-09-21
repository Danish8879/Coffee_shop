from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('first_name', 'last_name', 'email', 'address', 'phone')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    # Reject phone values that do not contain a practical number of digits.
    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digit_count = sum(character.isdigit() for character in phone)
        if digit_count < 7:
            raise forms.ValidationError('Enter a valid phone number.')
        return phone
