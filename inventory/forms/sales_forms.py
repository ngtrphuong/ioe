from django import forms
from django.core.exceptions import ValidationError

from inventory.models import Sale, SaleItem, Product, Member
from inventory.models.inventory import check_inventory


class SaleForm(forms.ModelForm):
    # Add member search field for quick lookup
    member_search = forms.CharField(
        max_length=100,
        label='Member Search',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number or member name',
            'aria-label': 'Member Search',
            'autocomplete': 'off',  # prevent autocomplete
            'style': 'height: 48px; font-size: 16px;',
            'inputmode': 'search',  # show search keyboard on mobile
            'data-bs-toggle': 'tooltip',
            'title': 'You can enter phone number or member name to search.'
        })
    )
    
    # Add method to get form warnings
    def get_warnings(self):
        """Get warning information during form validation (information that doesn't prevent submission but needs to alert the user)"""
        return getattr(self, '_warnings', {})
    
    class Meta:
        model = Sale
        fields = ['remark']
        widgets = {
            'remark': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Sales remark (optional)',
                'aria-label': 'Remark'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add helper classes for responsive layout
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # Add bottom margin
            })


class SaleItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Actual Selling Price',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'price-input form-control',
            'placeholder': 'Actual Selling Price',
            'inputmode': 'decimal',  # show numeric keyboard on mobile with decimal point
            'aria-label': 'Actual Selling Price',
            'autocomplete': 'off'  # prevent autocomplete
        })
    )
    
    # Add barcode scan field for quick product addition
    barcode = forms.CharField(
        max_length=100,
        label='Scan Barcode',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Scan product barcode',
            'aria-label': 'Scan Barcode',
            'autocomplete': 'off',  # prevent autocomplete
            'autofocus': True,  # auto-focus
            'style': 'height: 48px; font-size: 16px;'  # increase touch area and font size
        })
    )
    
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'price', 'actual_price']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control form-select product-select',
                'aria-label': 'Product',
                'style': 'height: 48px; font-size: 16px;'  # increase touch area and font size
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'quantity-input form-control',
                'min': '1',
                'value': '1',
                'step': '1',
                'placeholder': 'Quantity',
                'inputmode': 'numeric',  # show numeric keyboard on mobile
                'aria-label': 'Quantity',
                'autocomplete': 'off',  # prevent autocomplete
                'style': 'height: 48px; font-size: 16px;'  # increase touch area and font size
            }),
            'price': forms.NumberInput(attrs={
                'class': 'price-input form-control',
                'step': '0.01',
                'placeholder': 'Standard Price',
                'inputmode': 'decimal',  # show numeric keyboard on mobile with decimal point
                'aria-label': 'Standard Price',
                'readonly': 'readonly',  # standard price cannot be edited
                'style': 'height: 48px; font-size: 16px;'  # increase touch area and font size
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use select_related for better query performance
        self.fields['product'].queryset = Product.objects.all().select_related('category')
        
        # Add helper classes for responsive layout
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # Add bottom margin
            })
            
        # Mark warning information list
        self._warnings = {}
        
        # If instance already exists, set default actual price
        if self.instance and self.instance.pk:
            self.initial['actual_price'] = self.instance.actual_price
            
            # For existing sale items, product cannot be changed
            self.fields['product'].widget.attrs['readonly'] = 'readonly'
            self.fields['product'].widget.attrs['disabled'] = 'disabled'
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError('Sale quantity must be greater than 0')
        return quantity
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            # Check inventory
            if not self.instance.pk:  # Only new sale items check inventory
                if not check_inventory(product, quantity):
                    self._warnings['inventory'] = f'Warning: Product "{product.name}" has insufficient inventory; this sale quantity may result in negative inventory.'
                
            # Use default price if actual_price is not set
            if cleaned_data.get('actual_price') is None:
                cleaned_data['actual_price'] = product.price
                
            # If actual_price < 50% of standard price, add warning
            if cleaned_data.get('actual_price') < product.price * 0.5:
                self._warnings['low_price'] = f'Warning: Actual selling price for "{product.name}" is less than 50% of standard price. Please confirm.'
                
            # If actual_price > 200% of standard price, add warning
            if cleaned_data.get('actual_price') > product.price * 2:
                self._warnings['high_price'] = f'Warning: Actual selling price for "{product.name}" exceeds 200% of standard price. Please confirm.'
            
        return cleaned_data
    
    def get_warnings(self):
        """Get warning information during form validation (information that doesn't prevent submission but needs to alert the user)"""
        return self._warnings 