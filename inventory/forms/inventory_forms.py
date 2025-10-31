from django import forms

from inventory.models import InventoryTransaction, Product


class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control form-select',
                'aria-label': 'Product',
                'style': 'height: 48px; font-size: 16px;'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': 'Quantity',
                'inputmode': 'numeric',  # Show numeric keyboard on mobile
                'aria-label': 'Quantity',
                'autocomplete': 'off',  # Prevent browser autofill
                'pattern': '[0-9]*',  # HTML5 only allows numbers
                'style': 'height: 48px; font-size: 16px;'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Remarks',
                'aria-label': 'Remarks'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optimize queryset
        self.fields['product'].queryset = Product.objects.all().select_related('category')
        # Add responsive layout helper class
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # Add margin-bottom
            })
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('Quantity must be greater than 0')
        return quantity 