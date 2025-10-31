from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .product import Product


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.PROTECT, verbose_name='Product')
    quantity = models.IntegerField(default=0, verbose_name='Stock Quantity')
    warning_level = models.IntegerField(default=10, verbose_name='Warning Level')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    def clean(self):
        if self.quantity < 0:
            raise ValidationError('Stock quantity cannot be negative')
        if self.warning_level < 0:
            raise ValidationError('Warning level cannot be negative')
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.warning_level
    
    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'
        permissions = (
            ("can_view_item", "Can view items"),
            ("can_add_item", "Can add items"),
            ("can_change_item", "Can change items"),
            ("can_delete_item", "Can delete items"),
            ("can_export_item", "Can export items"),
            ("can_import_item", "Can import items"),
            ("can_allocate_item", "Can allocate items"),
            ("can_checkin_item", "Can check in items"),
            ("can_checkout_item", "Can check out items"),
            ("can_adjust_item", "Can adjust item inventory"),
            ("can_return_item", "Can return items"),
            ("can_move_item", "Can move items"),
            ("can_manage_backup", "Can manage backups"),
        )
    
    def __str__(self):
        return f'{self.product.name} - {self.quantity}'


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUST', 'Adjustment'),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Product')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='Transaction Type')
    quantity = models.IntegerField(verbose_name='Quantity')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Operator')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'
    
    def __str__(self):
        return f'{self.product.name} - {self.get_transaction_type_display()} - {self.quantity}'


# Inventory utility functions
def check_inventory(product, quantity):
    """Check if inventory is sufficient"""
    try:
        inventory = Inventory.objects.get(product=product)
        return inventory.quantity >= quantity
    except Inventory.DoesNotExist:
        return False


def update_inventory(product, quantity, transaction_type, operator, notes=''):
    """Update inventory and record transaction"""
    try:
        # Get or create inventory record
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            defaults={'quantity': 0}
        )
        
        # Update inventory quantity
        old_quantity = inventory.quantity
        inventory.quantity += quantity
        
        # Ensure inventory is not negative
        if inventory.quantity < 0:
            raise ValidationError(f"Insufficient inventory: {product.name}, current stock: {old_quantity}, requested quantity: {abs(quantity)}")
        
        inventory.save()
        
        # Record inventory transaction
        transaction = InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=abs(quantity),  # Store absolute value
            operator=operator,
            notes=notes
        )
        
        return True, inventory, transaction
    except Exception as e:
        return False, None, str(e)


class StockAlert(models.Model):
    """Stock Alert Model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Product')
    alert_type = models.CharField(
        max_length=20, 
        choices=[
            ('low_stock', 'Low Stock'),
            ('expiring', 'Expiring Soon'),
            ('overstock', 'Overstock')
        ],
        verbose_name='Alert Type'
    )
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Resolved At')
    
    class Meta:
        verbose_name = 'Stock Alert'
        verbose_name_plural = 'Stock Alerts'
        
    def __str__(self):
        return f'{self.product.name} - {self.get_alert_type_display()}' 