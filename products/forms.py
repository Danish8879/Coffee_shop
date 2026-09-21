from django import forms


class ProductOptionsForm(forms.Form):
    grind = forms.ChoiceField(choices=(
        ('whole-beans', 'Whole beans'),
        ('french-press', 'French press'),
        ('espresso-machine', 'Espresso machine'),
        ('turkish-grind', 'Turkish grind'),
    ))
    weight = forms.TypedChoiceField(
        choices=((250, '250 g'), (500, '500 g'), (750, '750 g'), (1000, '1 kg')),
        coerce=int,
    )

    # Ensure the selected weight is one of the supported packet sizes.
    def clean_weight(self):
        weight = self.cleaned_data['weight']
        if weight not in (250, 500, 750, 1000):
            raise forms.ValidationError('Choose a valid packet weight.')
        return weight
