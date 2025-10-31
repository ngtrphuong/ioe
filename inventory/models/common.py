from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class OperationLog(models.Model):
    """
    General operation log model to record all types of operations in the system,
    supporting linkage to different objects.
    """
    OPERATION_TYPES = [
        ('SALE', 'Sale'),
        ('INVENTORY', 'Inventory Adjustment'),
        ('MEMBER', 'Member Management'),
        ('INVENTORY_CHECK', 'Inventory Check'),
        ('OTHER', 'Other')
    ]

    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Operator')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name='Operation Type')
    details = models.TextField(verbose_name='Details')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')
    related_object_id = models.PositiveIntegerField(verbose_name='Related Object ID')
    related_content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, verbose_name='Related Content Type')

    class Meta:
        verbose_name = 'Operation Log'
        verbose_name_plural = 'Operation Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.operator.username} - {self.get_operation_type_display()} - {self.timestamp}'


class SystemConfig(models.Model):
    """System configuration model"""
    company_name = models.CharField(max_length=100, verbose_name="Company Name", default="My Store")
    company_address = models.TextField(verbose_name="Company Address", blank=True, null=True)
    company_phone = models.CharField(max_length=20, verbose_name="Phone", blank=True, null=True)
    company_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    company_website = models.URLField(verbose_name="Website", blank=True, null=True)
    company_logo = models.ImageField(upload_to='logos/', verbose_name="Company Logo", blank=True, null=True)
    
    # Barcode settings
    barcode_width = models.IntegerField(verbose_name="Barcode Width", default=300)
    barcode_height = models.IntegerField(verbose_name="Barcode Height", default=100)
    barcode_font_size = models.IntegerField(verbose_name="Barcode Font Size", default=12)
    barcode_show_price = models.BooleanField(verbose_name="Show Price", default=True)
    barcode_show_name = models.BooleanField(verbose_name="Show Product Name", default=True)
    barcode_show_company = models.BooleanField(verbose_name="Show Company Name", default=True)
    
    # Printing settings
    receipt_header = models.TextField(verbose_name="Receipt Header", blank=True, null=True)
    receipt_footer = models.TextField(verbose_name="Receipt Footer", blank=True, null=True)
    
    # System settings
    enable_low_stock_alert = models.BooleanField(verbose_name="Enable Low Stock Alert", default=True)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Default Tax Rate", default=0)
    currency_symbol = models.CharField(max_length=10, verbose_name="Currency Symbol", default="VNĐ")
    timezone = models.CharField(max_length=50, verbose_name="Timezone", default="Asia/Shanghai")
    
    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
    
    def __str__(self):
        return self.company_name 