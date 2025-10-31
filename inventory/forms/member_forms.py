from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from ..models.member import Member, MemberLevel, RechargeRecord


class MemberForm(forms.ModelForm):
    """Member Form"""
    class Meta:
        model = Member
        fields = ['name', 'phone', 'gender', 'birthday', 'level', 'email', 'member_id', 'address', 'notes', 'is_active']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('phone', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('gender', css_class='form-group col-md-4 mb-0'),
                Column('birthday', css_class='form-group col-md-4 mb-0'),
                Column('member_id', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('level', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            'notes',
            'is_active',
            Submit('submit', 'Save', css_class='btn btn-primary')
        )
    
    def clean_phone(self):
        """Phone number validation"""
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError('Phone number cannot be empty')
        
        # Check format
        import re
        if not re.match(r'^\d{11}$', phone):
            raise forms.ValidationError('Please enter an 11-digit phone number')
        
        # Check uniqueness (exclude current instance)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # Modify check
            if Member.objects.exclude(pk=instance.pk).filter(phone=phone).exists():
                raise forms.ValidationError('This phone number has already been registered')
        else:
            # New check
            if Member.objects.filter(phone=phone).exists():
                raise forms.ValidationError('This phone number has already been registered')
                
        return phone


class MemberLevelForm(forms.ModelForm):
    """Member Level Form"""
    class Meta:
        model = MemberLevel
        fields = ['name', 'discount', 'points_threshold', 'color', 'priority', 'is_default', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            Row(
                Column('discount', css_class='form-group col-md-6 mb-0'),
                Column('points_threshold', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('color', css_class='form-group col-md-4 mb-0'),
                Column('priority', css_class='form-group col-md-4 mb-0'),
                Column('is_default', css_class='form-group col-md-2 mb-0'),
                Column('is_active', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Save', css_class='btn btn-primary')
        )
    
    def clean_discount(self):
        """Discount validation"""
        discount = self.cleaned_data.get('discount')
        if discount < 0 or discount > 1:
            raise forms.ValidationError('Discount rate must be between 0 and 1')
        return discount
    
    def clean(self):
        """Validate the whole form"""
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        
        # If set to default, check for existing default
        if is_default and not self.instance.pk:
            if MemberLevel.objects.filter(is_default=True).exists():
                self.add_error('is_default', 'There is already a default level; only one is allowed at a time')
        return cleaned_data


class RechargeForm(forms.ModelForm):
    """Member recharge form"""
    class Meta:
        model = RechargeRecord
        fields = ['amount', 'actual_amount', 'payment_method', 'remark']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('amount', css_class='form-group col-md-6 mb-0'),
                Column('actual_amount', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'payment_method',
            'remark',
            Submit('submit', 'Confirm Recharge', css_class='btn btn-primary')
        )
        
        # Auto-fill actual_amount with amount
        self.fields['actual_amount'].initial = self.fields['amount'].initial


class MemberImportForm(forms.Form):
    """Batch member import form"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Please upload a CSV format member data file, must include name and phone columns'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'csv_file',
            Div(
                Submit('submit', 'Import', css_class='btn btn-primary'),
                css_class='form-group'
            )
        )
        
    def clean_csv_file(self):
        """CSV file format validation"""
        csv_file = self.cleaned_data.get('csv_file')
        if not csv_file:
            raise forms.ValidationError('Please select a file')
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('Please upload a CSV file')
            
        # File size limit (2MB)
        if csv_file.size > 2 * 1024 * 1024:
            raise forms.ValidationError('File size cannot exceed 2MB')
            
        return csv_file 