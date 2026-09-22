from django import forms

GRIND_CHOICES = (
    ('whole-beans', 'Whole beans'),
    ('french-press', 'French press'),
    ('espresso-machine', 'Espresso machine'),
    ('turkish-grind', 'Turkish grind'),
)
WEIGHT_CHOICES = ((250, '250 g'), (500, '500 g'), (750, '750 g'), (1000, '1 kg'))
MAX_ORDER_QUANTITY = 20


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=MAX_ORDER_QUANTITY, initial=1)


class ProductOptionsForm(QuantityForm):
    grind = forms.ChoiceField(choices=GRIND_CHOICES)
    weight = forms.TypedChoiceField(choices=WEIGHT_CHOICES, coerce=int)


# Return the add-to-cart form that matches the product: bean options or quantity only.
def get_add_to_cart_form(product, data=None):
    form_class = ProductOptionsForm if product.has_bean_options else QuantityForm
    return form_class(data)
