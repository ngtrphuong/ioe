from django import forms
from django.core.validators import FileExtensionValidator
from inventory.models import Product, Category, Inventory
import csv
import io

class BatchProductImportForm(forms.Form):
    """
    Batch import product form
    """
    file = forms.FileField(
        label='CSV File',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text='Please upload a CSV file containing product information.',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label='Default Category',
        required=False,
        help_text='Used if no category is specified per row in the CSV.',
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )
    
    update_existing = forms.BooleanField(
        label='Update Existing Products',
        required=False,
        initial=False,
        help_text='If checked, existing product information will be updated.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate CSV format
            try:
                # Read CSV file
                csv_file = file.read().decode('utf-8')
                csv_data = csv.reader(io.StringIO(csv_file))
                
                # Get header
                headers = next(csv_data)
                
                # Check required columns
                required_columns = ['barcode', 'name', 'price', 'cost']
                missing_columns = [col for col in required_columns if col not in headers]
                
                if missing_columns:
                    raise forms.ValidationError(f"CSV is missing required columns: {', '.join(missing_columns)}")
                
                # Reset file pointer
                file.seek(0)
                
            except Exception as e:
                raise forms.ValidationError(f"Invalid CSV format: {str(e)}")
        
        return file

class BatchInventoryUpdateForm(forms.Form):
    """
    Batch inventory adjustment form
    """
    file = forms.FileField(
        label='CSV File',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text='Please upload a CSV file with product barcode and inventory quantity.',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    adjustment_type = forms.ChoiceField(
        label='Adjustment Type',
        choices=[
            ('set', 'Set to specified quantity'),
            ('add', 'Increase by specified quantity'),
            ('subtract', 'Decrease by specified quantity'),
        ],
        initial='set',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    notes = forms.CharField(
        label='Notes',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text='Reason or explanation for the batch adjustment.'
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            try:
                # Read CSV file
                csv_file = file.read().decode('utf-8')
                csv_data = csv.reader(io.StringIO(csv_file))
                
                # Get header
                headers = next(csv_data)
                
                # Check required columns
                required_columns = ['barcode', 'quantity']
                missing_columns = [col for col in required_columns if col not in headers]
                
                if missing_columns:
                    raise forms.ValidationError(f"CSV is missing required columns: {', '.join(missing_columns)}")
                
                # Validate rows
                row_number = 1  # header is row 1
                errors = []
                
                for row in csv_data:
                    row_number += 1
                    if len(row) != len(headers):
                        errors.append(f"Row {row_number}: Number of columns does not match header")
                        continue
                    
                    # Create row dict
                    row_data = dict(zip(headers, row))
                    
                    # Validate barcode
                    barcode = row_data.get('barcode', '').strip()
                    if not barcode:
                        errors.append(f"Row {row_number}: Barcode cannot be empty")
                    
                    # Validate quantity
                    quantity = row_data.get('quantity', '').strip()
                    try:
                        quantity = int(quantity)
                        if quantity < 0 and self.cleaned_data.get('adjustment_type') == 'set':
                            errors.append(f"Row {row_number}: Quantity cannot be negative when setting inventory")
                    except ValueError:
                        errors.append(f"Row {row_number}: Quantity must be an integer")
                
                if errors:
                    raise forms.ValidationError(errors)
                
                # Reset file pointer
                file.seek(0)
                
            except Exception as e:
                if not isinstance(e, forms.ValidationError):
                    raise forms.ValidationError(f"CSV processing error: {str(e)}")
                raise
        
        return file

class ProductBatchDeleteForm(forms.Form):
    """
    Batch delete product form
    """
    product_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    confirm = forms.BooleanField(
        label='Confirm Deletion',
        required=True,
        help_text='I understand this is irreversible and confirm deletion of the selected products.'
    )
    
    def clean_product_ids(self):
        product_ids_str = self.cleaned_data.get('product_ids')
        if not product_ids_str:
            raise forms.ValidationError('No products selected')
        
        try:
            product_ids = [int(id.strip()) for id in product_ids_str.split(',') if id.strip()]
            if not product_ids:
                raise forms.ValidationError('No products selected')
            return product_ids
        except ValueError:
            raise forms.ValidationError('Invalid product ID format')