from django import forms
from django.utils import timezone
from datetime import timedelta, datetime, date

from inventory.models import Category, Store


class DateRangeForm(forms.Form):
    """General date range form for reports"""
    
    PERIOD_CHOICES = [
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
        ('hour', 'Hour'),  # New hourly statistics option
        ('minute', 'Minute'),  # New minute statistics option, for real-time monitoring
    ]
    
    CACHE_PRESETS = [
        (5, '5 Minutes'),  # New shorter cache time
        (15, '15 Minutes'),
        (30, '30 Minutes'),
        (60, '1 Hour'),
        (180, '3 Hours'),
        (360, '6 Hours'),
        (720, '12 Hours'),
        (1440, '24 Hours'),
        (2880, '2 Days'),  # New longer cache time
        (10080, '7 Days'),  # New weekly cache
        (0, 'No Cache'),  # New no cache option
    ]
    
    # Preset date range options
    DATE_RANGE_PRESETS = [
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_quarter', 'This Quarter'),
        ('last_quarter', 'Last Quarter'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('last_3_days', 'Last 3 Days'),  # New shorter time range
        ('last_7_days', 'Last 7 Days'),
        ('last_14_days', 'Last 14 Days'),  # New two-week option
        ('last_30_days', 'Last 30 Days'),
        ('last_60_days', 'Last 60 Days'),  # New more options
        ('last_90_days', 'Last 90 Days'),
        ('last_180_days', 'Last 180 Days'),  # New half-year option
        ('last_365_days', 'Last 365 Days'),
        ('current_week_to_date', 'Current Week to Date'),  # New to date option
        ('current_month_to_date', 'Current Month to Date'),
        ('current_quarter_to_date', 'Current Quarter to Date'),
        ('current_year_to_date', 'Current Year to Date'),
        ('custom', 'Custom Range'),
    ]
    
    date_range_preset = forms.ChoiceField(
        label='Preset Date Range',
        choices=DATE_RANGE_PRESETS,
        initial='last_30_days',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Preset Date Range',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        }),
        help_text='Select a preset date range to quickly set start and end dates.'
    )
    
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'aria-label': 'Start Date',
            'style': 'height: 48px; font-size: 16px;',  # Increase touch area and font size
            'data-bs-toggle': 'tooltip',
            'title': 'Report start date'
        }),
        initial=timezone.now().date() - timedelta(days=30)
    )
    
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'aria-label': 'End Date',
            'style': 'height: 48px; font-size: 16px;',  # Increase touch area and font size
            'data-bs-toggle': 'tooltip',
            'title': 'Report end date'
        }),
        initial=timezone.now().date()
    )
    
    period = forms.ChoiceField(
        label='Time Period',
        choices=PERIOD_CHOICES,
        initial='day',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Time Period'
        })
    )
    
    use_cache = forms.BooleanField(
        label='Use Cache',
        required=False,
        initial=True,
        help_text='Using cache can improve report generation speed, but may not show the latest data.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Use Cache',
            'data-bs-toggle': 'tooltip',
            'title': 'Enabling cache significantly improves report loading speed',
            'style': 'width: 20px; height: 20px;'  # Increase touch area
        })
    )
    
    cache_timeout = forms.IntegerField(
        label='Cache Time (Minutes)',
        required=False,
        initial=60,
        min_value=0,  # Allow setting to 0 to mean no cache
        max_value=10080,  # 7 days
        help_text='The effective time for cached data, 0 means no cache.',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '5',
            'aria-label': 'Cache Time',
            'inputmode': 'numeric',  # Show numeric keyboard on mobile devices
            'data-bs-toggle': 'tooltip',
            'title': 'Set the effective time for report data cache (minutes)',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    cache_preset = forms.ChoiceField(
        label='Preset Cache Time',
        choices=CACHE_PRESETS,
        required=False,
        initial=60,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Preset Cache Time',
            'data-bs-toggle': 'tooltip',
            'title': 'Select a preset cache time',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    force_refresh = forms.BooleanField(
        label='Force Refresh',
        required=False,
        initial=False,
        help_text='Force re-generate report data, ignoring cache.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Force Refresh',
            'data-bs-toggle': 'tooltip',
            'title': 'Force re-generate report data, ignoring cache.',
            'style': 'width: 20px; height: 20px;'  # Increase touch area
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add helper classes for responsive layout
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # Add bottom margin
            })
    
    def _get_date_range_from_preset(self, preset):
        """Get date range based on preset value"""
        today = timezone.now().date()
        
        # Calculate the start date of the current week (Monday)
        def get_week_start(d):
            return d - timedelta(days=d.weekday())
        
        # Calculate the start date of the current month
        def get_month_start(d):
            return date(d.year, d.month, 1)
        
        # Calculate the start date of the current quarter
        def get_quarter_start(d):
            quarter = (d.month - 1) // 3 + 1
            return date(d.year, 3 * quarter - 2, 1)
        
        # Calculate the start date of the current year
        def get_year_start(d):
            return date(d.year, 1, 1)
            
        if preset == 'today':
            return today, today
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif preset == 'this_week':
            week_start = get_week_start(today)
            return week_start, today
        elif preset == 'last_week':
            this_week_start = get_week_start(today)
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start - timedelta(days=1)
            return last_week_start, last_week_end
        elif preset == 'this_month':
            month_start = get_month_start(today)
            return month_start, today
        elif preset == 'last_month':
            this_month_start = get_month_start(today)
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = get_month_start(last_month_end)
            return last_month_start, last_month_end
        elif preset == 'this_quarter':
            quarter_start = get_quarter_start(today)
            return quarter_start, today
        elif preset == 'last_quarter':
            this_quarter_start = get_quarter_start(today)
            last_quarter_end = this_quarter_start - timedelta(days=1)
            # Find the start of the previous quarter
            if this_quarter_start.month == 1:  # If it's the first quarter
                last_quarter_start = date(this_quarter_start.year - 1, 10, 1)
            else:
                last_quarter_start = date(this_quarter_start.year, this_quarter_start.month - 3, 1)
            return last_quarter_start, last_quarter_end
        elif preset == 'this_year':
            year_start = get_year_start(today)
            return year_start, today
        elif preset == 'last_year':
            this_year_start = get_year_start(today)
            last_year_end = this_year_start - timedelta(days=1)
            last_year_start = date(last_year_end.year, 1, 1)
            return last_year_start, last_year_end
        elif preset == 'last_3_days':
            return today - timedelta(days=2), today
        elif preset == 'last_7_days':
            return today - timedelta(days=6), today
        elif preset == 'last_14_days':
            return today - timedelta(days=13), today
        elif preset == 'last_30_days':
            return today - timedelta(days=29), today
        elif preset == 'last_60_days':
            return today - timedelta(days=59), today
        elif preset == 'last_90_days':
            return today - timedelta(days=89), today
        elif preset == 'last_180_days':
            return today - timedelta(days=179), today
        elif preset == 'last_365_days':
            return today - timedelta(days=364), today
        elif preset == 'current_week_to_date':
            return get_week_start(today), today
        elif preset == 'current_month_to_date':
            return get_month_start(today), today
        elif preset == 'current_quarter_to_date':
            return get_quarter_start(today), today
        elif preset == 'current_year_to_date':
            return get_year_start(today), today
            
        # If no preset matches or custom is selected, return None
        return None, None
    
    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get('date_range_preset')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # If a preset date range is selected (not custom), calculate the corresponding start and end dates
        if preset and preset != 'custom':
            start_date, end_date = self._get_date_range_from_preset(preset)
            if start_date and end_date:
                cleaned_data['start_date'] = start_date
                cleaned_data['end_date'] = end_date
                
        # Ensure start date is not later than end date
        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', 'Start date cannot be later than end date.')
            
        # If a preset cache time is set, update cache timeout
        cache_preset = cleaned_data.get('cache_preset')
        if cache_preset:
            try:
                cleaned_data['cache_timeout'] = int(cache_preset)
            except (ValueError, TypeError):
                pass  # If conversion fails, keep original
                
        # If force refresh, disable cache
        if cleaned_data.get('force_refresh'):
            cleaned_data['use_cache'] = False
            cleaned_data['cache_timeout'] = 0
            
        # Give smaller date ranges a smaller cache time, unless user explicitly chooses
        if not cache_preset and preset in ('today', 'yesterday', 'last_3_days'):
            cleaned_data['cache_timeout'] = min(cleaned_data.get('cache_timeout', 60), 30)  # Max 30 minutes
            
        return cleaned_data
    
    def get_date_range_display(self):
        """Get the display text for the date range, for report titles, etc."""
        preset = self.cleaned_data.get('date_range_preset')
        
        # If a preset is selected, return the preset display name
        if preset and preset != 'custom':
            for value, label in self.DATE_RANGE_PRESETS:
                if value == preset:
                    return label
                    
        # If it's a custom range, display the actual date range
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        if start_date and end_date:
            if start_date == end_date:
                return f"{start_date.strftime('%Y-%m-%d')}"
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            
        # Default case
        return 'Custom Date Range'


class TopProductsForm(DateRangeForm):
    """Form for hot product reports"""
    limit = forms.IntegerField(
        label='Display Quantity',
        initial=10,
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class InventoryTurnoverForm(DateRangeForm):
    """Form for inventory turnover reports"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )


# Add missing form classes
class ReportFilterForm(DateRangeForm):
    """General report filter form, inheriting DateRangeForm and adding category and store filters"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Product Category',
            'data-bs-toggle': 'tooltip',
            'title': 'Filter report data by product category',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True),  # Restore is_active filter, only show active stores
        required=False,
        empty_label="All Stores",
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Store',
            'data-bs-toggle': 'tooltip',
            'title': 'Filter report data by store',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Handle case where store is empty
        if Store.objects.count() == 0:
            self.fields.pop('store', None)


class SalesReportForm(ReportFilterForm):
    """Sales report specific form, inheriting ReportFilterForm and adding sales-related filters"""
    SALES_TYPE_CHOICES = [
        ('all', 'All Sales'),
        ('retail', 'Retail Sales'),
        ('wholesale', 'Wholesale Sales'),
        ('member', 'Member Sales'),
        ('online', 'Online Sales'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('all', 'All Payment Methods'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('alipay', 'Alipay'),
        ('wechat', 'WeChat Pay'),
        ('other', 'Other'),
    ]
    
    SORT_CHOICES = [
        ('date', 'By Date'),
        ('amount', 'By Amount'),
        ('profit', 'By Profit'),
        ('quantity', 'By Quantity'),
    ]
    
    sales_type = forms.ChoiceField(
        label='Sales Type',
        choices=SALES_TYPE_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Sales Type',
            'data-bs-toggle': 'tooltip',
            'title': 'Filter by sales type',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    payment_method = forms.ChoiceField(
        label='Payment Method',
        choices=PAYMENT_METHOD_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Payment Method',
            'data-bs-toggle': 'tooltip',
            'title': 'Filter by payment method',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    min_amount = forms.DecimalField(
        label='Minimum Amount',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'aria-label': 'Minimum Amount',
            'placeholder': 'Minimum sales amount',
            'inputmode': 'decimal',  # Show numeric keyboard on mobile devices
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    max_amount = forms.DecimalField(
        label='Maximum Amount',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'aria-label': 'Maximum Amount',
            'placeholder': 'Maximum sales amount',
            'inputmode': 'decimal',  # Show numeric keyboard on mobile devices
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    sort_by = forms.ChoiceField(
        label='Sort By',
        choices=SORT_CHOICES,
        required=False,
        initial='date',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': 'Sort By',
            'data-bs-toggle': 'tooltip',
            'title': 'Choose how to sort report data',
            'style': 'height: 48px; font-size: 16px;'  # Increase touch area and font size
        })
    )
    
    include_tax = forms.BooleanField(
        label='Include Tax',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': 'Include Tax',
            'data-bs-toggle': 'tooltip',
            'title': 'Whether to include tax in the report',
            'style': 'width: 20px; height: 20px;'  # Increase touch area
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        # Validate minimum amount is not greater than maximum amount
        if min_amount and max_amount and min_amount > max_amount:
            self.add_error('min_amount', 'Minimum amount cannot be greater than maximum amount.')
            
        return cleaned_data 