from django import forms
from django.utils import timezone
from inventory.models import Category, InventoryCheck, InventoryCheckItem


class InventoryCheckForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='Product Category',
        help_text='Optional. Only products in this category will be included in the check.',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Product Category',
            'style': 'height: 48px; font-size: 16px;',
            'data-bs-toggle': 'tooltip',
            'title': 'Select category for inventory check',
            'data-mobile-friendly': 'true'
        })
    )
    
    scheduled_date = forms.DateField(
        label='Scheduled Check Date',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'aria-label': 'Scheduled Check Date',
            'style': 'height: 48px; font-size: 16px;',
            'data-bs-toggle': 'tooltip',
            'title': 'Set a planned date for this inventory check',
            'min': timezone.now().date().isoformat(),
            'data-mobile-friendly': 'true'
        }),
        help_text='Optional, set a planned date for this inventory check.'
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('low', 'Low Priority'),
            ('normal', 'Normal'),
            ('high', 'High Priority'),
            ('urgent', 'Urgent')
        ],
        required=False,
        initial='normal',
        label='Priority',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Priority',
            'style': 'height: 48px; font-size: 16px;',
            'data-mobile-friendly': 'true'
        }),
        help_text='Set priority for this inventory check task.'
    )
    
    class Meta:
        model = InventoryCheck
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Check Name',
                'aria-label': 'Check Name',
                'style': 'height: 48px; font-size: 16px;',
                'autocomplete': 'off',
                'autofocus': True,
                'minlength': '2',
                'maxlength': '100',
                'required': 'required',
                'data-mobile-friendly': 'true'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Check Description',
                'aria-label': 'Check Description',
                'style': 'font-size: 16px;',
                'maxlength': '500',
                'data-mobile-friendly': 'true'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optimize queryset
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        # Add responsive layout class
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',
                'autocapitalize': 'off',
            })
        # Set default placeholder for mobile devices if missing
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label


class InventoryCheckItemForm(forms.ModelForm):
    barcode_scan = forms.CharField(
        max_length=100,
        label='Scan Barcode',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Scan product barcode',
            'inputmode': 'numeric',
            'aria-label': 'Scan Barcode',
            'autocomplete': 'off',
            'autofocus': True,
            'style': 'height: 48px; font-size: 16px;'
        }),
        help_text='Quickly locate a product by scanning its barcode.'
    )
    
    class Meta:
        model = InventoryCheckItem
        fields = ['actual_quantity', 'notes']
        widgets = {
            'actual_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Actual Quantity',
                'inputmode': 'numeric',
                'aria-label': 'Actual Quantity',
                'autocomplete': 'off',
                'pattern': '[0-9]*',
                'style': 'height: 48px; font-size: 16px;'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Remarks',
                'aria-label': 'Remarks',
                'style': 'font-size: 16px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add responsive layout
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',
                'autocapitalize': 'off',
            })
    
    def clean_actual_quantity(self):
        actual_quantity = self.cleaned_data.get('actual_quantity')
        if actual_quantity is not None and actual_quantity < 0:
            raise forms.ValidationError('Actual quantity cannot be negative')
        return actual_quantity


class InventoryCheckApproveForm(forms.Form):
    adjust_inventory = forms.BooleanField(
        required=False,
        label='Adjust Inventory',
        help_text='Check to automatically adjust inventory to match actual quantity.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Adjust Inventory',
            'style': 'width: 20px; height: 20px;'
        })
    )
    
    confirm = forms.BooleanField(
        required=True,
        label='Confirm Approval',
        help_text='I have checked all inventory check data and confirm its accuracy.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Confirm Approval',
            'style': 'width: 20px; height: 20px;'
        })
    )
    
    notes = forms.CharField(
        required=False,
        label='Approval Remarks',
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Remarks (optional)',
            'aria-label': 'Approval Remarks'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': field.widget.attrs.get('class', '') + ' mb-2',
                })
    def clean(self):
        cleaned_data = super().clean()
        confirm = cleaned_data.get('confirm')
        if not confirm:
            self.add_error('confirm', 'You must confirm approval to proceed.')
        return cleaned_data 