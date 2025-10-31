import re
from django import forms
from django.forms import inlineformset_factory
from inventory.models import Product, Category, ProductImage, ProductBatch, Supplier


class ProductForm(forms.ModelForm):
    barcode = forms.CharField(
        max_length=100,
        label='Product Barcode',
        help_text='Supports standard barcode formats such as EAN-13, UPC, ISBN, etc.',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Please enter the product barcode',
            'autocomplete': 'off',  # Prevent autofill
            'inputmode': 'numeric',
            'pattern': '[A-Za-z0-9-]+',
            'aria-label': 'Product Barcode'
        })
    )
    
    # Add warning level field
    warning_level = forms.IntegerField(
        label='Warning Inventory',
        help_text='An alert will be triggered when inventory falls below this quantity',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'placeholder': 'Warning Quantity',
            'aria-label': 'Warning Inventory'
        })
    )
    
    class Meta:
        model = Product
        fields = ['barcode', 'name', 'category', 'color', 'size', 'description', 'price', 'cost', 'image', 'specification', 'manufacturer', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please enter product name', 'aria-label': 'Product Name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Sale Price', 'inputmode': 'decimal', 'aria-label': 'Sale Price'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Cost Price', 'inputmode': 'decimal', 'aria-label': 'Cost Price'}),
            'specification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specification', 'aria-label': 'Specification'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer', 'aria-label': 'Manufacturer'}),
            'category': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': 'Product Category'}),
            'color': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': 'Color'}),
            'size': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': 'Size'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'aria-label': 'Product Image'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'aria-label': 'Active'}),
        }
        
    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        if barcode:
            # Remove spaces and other invisible characters
            barcode = re.sub(r'\s', '', barcode).strip()
            
            # Check if only contains numbers, letters and hyphens
            if not all(c.isalnum() or c == '-' for c in barcode):
                raise forms.ValidationError('Barcode can only contain numbers, letters, and hyphens')
            
            # Check if barcode already exists (exclude current instance)
            existing = Product.objects.filter(barcode=barcode)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise forms.ValidationError('This barcode already exists, please do not add duplicates')
                
            # Check common barcode formats
            # Standard barcode formats
            # EAN-13: 13 digits
            # EAN-8: 8 digits
            # UPC-A: 12 digits
            # UPC-E: 8 digits, starts with 0
            # ISBN-13: 13 digits, usually starts with 978 or 979
            # ISBN-10: 10 digits or digits+X
            # JAN: Japanese product code, 13 digits, starts with 45 or 49
            # ITF-14: 14 digits, usually used for logistics packaging
            # GTIN-14: 14 digits, Global Trade Item Number
            # Code-39: Variable length, alphanumeric and specific symbols
            # Code-128: Variable length, all ASCII characters
            ean13_pattern = re.compile(r'^\d{13}$')
            ean8_pattern = re.compile(r'^\d{8}$')
            upc_pattern = re.compile(r'^\d{12}$')
            upc_e_pattern = re.compile(r'^0\d{7}$')
            isbn13_pattern = re.compile(r'^(978|979)\d{10}$')
            isbn10_pattern = re.compile(r'^\d{9}[\dX]$')
            jan_pattern = re.compile(r'^(45|49)\d{11}$')
            itf14_pattern = re.compile(r'^\d{14}$')
            gtin14_pattern = re.compile(r'^\d{14}$')
            
            # If does not match any standard format, add warning (but don't prevent saving)
            is_standard_format = (
                ean13_pattern.match(barcode) or
                ean8_pattern.match(barcode) or
                upc_pattern.match(barcode) or
                upc_e_pattern.match(barcode) or
                isbn13_pattern.match(barcode) or
                isbn10_pattern.match(barcode) or
                jan_pattern.match(barcode) or
                itf14_pattern.match(barcode) or
                gtin14_pattern.match(barcode)
            )
            
            if not is_standard_format:
                # Add warning, but don't prevent saving
                self.add_warning = 'Barcode format does not match standard formats, please confirm'
                
        return barcode
        
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        cost = cleaned_data.get('cost')
        
        if price is not None and cost is not None and price < cost:
            self.add_warning = 'Current sale price is below cost price, please confirm'
            
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category Name',
                'aria-label': 'Category Name',
                'style': 'height: 48px; font-size: 16px;',
                'autocomplete': 'off',  # Prevent autofill
                'autofocus': True  # Auto-focus
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Category Description',
                'rows': 3,
                'aria-label': 'Category Description',
                'style': 'font-size: 16px;'  # Increase font size
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add helper classes for responsive layout
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # Add bottom margin
                'autocapitalize': 'off',  # Prevent automatic capitalization of first letter
            })
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Remove extra spaces
            name = name.strip()
            
            # Check name length
            if len(name) < 2:
                raise forms.ValidationError('Category name must be at least 2 characters')
                
            # Check if a category with the same name already exists (excluding the current instance)
            existing = Category.objects.filter(name=name)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise forms.ValidationError('This category name already exists, please use another name')
                
        return name 


class ProductBatchForm(forms.ModelForm):
    """Product Batch Form"""
    class Meta:
        model = ProductBatch
        fields = ['batch_number', 'production_date', 'expiry_date', 'quantity', 'cost_price', 'supplier', 'remarks']
        widgets = {
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Batch Number',
                'aria-label': 'Batch Number'
            }),
            'production_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'aria-label': 'Production Date'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'aria-label': 'Expiry Date'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Quantity',
                'aria-label': 'Quantity'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Cost Price',
                'aria-label': 'Cost Price'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-control form-select',
                'aria-label': 'Supplier'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Remarks',
                'aria-label': 'Remarks'
            }),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise forms.ValidationError('Quantity cannot be negative')
        return quantity

    def clean_cost_price(self):
        cost_price = self.cleaned_data.get('cost_price')
        if cost_price is not None and cost_price < 0:
            raise forms.ValidationError('Cost price cannot be negative')
        return cost_price


# Create inline formset for product images
ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage,
    fields=('image', 'alt_text', 'order', 'is_primary'),
    extra=3,  # Default to 3 empty forms
    can_delete=True,  # Allow deletion
    widgets={
        'image': forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'aria-label': 'Image'
        }),
        'alt_text': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Image Description',
            'aria-label': 'Image Description'
        }),
        'order': forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'placeholder': 'Order',
            'aria-label': 'Order'
        }),
        'is_primary': forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Is Primary'
        }),
    }
)


class ProductBulkForm(forms.Form):
    """Bulk Create Product Form"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        label='Product Category',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Product Category'
        })
    )
    name_prefix = forms.CharField(
        max_length=100,
        label='Product Name Prefix',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Test Product',
            'aria-label': 'Product Name Prefix'
        })
    )
    name_suffix_start = forms.IntegerField(
        label='Starting Number',
        initial=1,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'step': '1',
            'placeholder': '1',
            'aria-label': 'Starting Number'
        })
    )
    name_suffix_end = forms.IntegerField(
        label='Ending Number',
        initial=10,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'step': '1',
            'placeholder': '10',
            'aria-label': 'Ending Number'
        })
    )
    retail_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Retail Price',
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Retail Price',
            'aria-label': 'Retail Price'
        })
    )
    wholesale_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Wholesale Price',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Wholesale Price (Optional)',
            'aria-label': 'Wholesale Price'
        })
    )
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Cost Price',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Cost Price (Optional)',
            'aria-label': 'Cost Price'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        suffix_start = cleaned_data.get('name_suffix_start')
        suffix_end = cleaned_data.get('name_suffix_end')
        
        if suffix_start and suffix_end and suffix_start > suffix_end:
            raise forms.ValidationError('Starting number cannot be greater than ending number')
        
        # Limit bulk creation to no more than 100
        if suffix_start and suffix_end and (suffix_end - suffix_start + 1) > 100:
            raise forms.ValidationError('Number of products to create cannot exceed 100')
        
        return cleaned_data


class ProductImportForm(forms.Form):
    """Product Import Form"""
    csv_file = forms.FileField(
        label='CSV File',
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
            'aria-label': 'CSV File'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # Check file type
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError('Please upload a CSV file')
            
            # Check file size, limit to 5MB
            if csv_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 5MB')
        
        return csv_file 