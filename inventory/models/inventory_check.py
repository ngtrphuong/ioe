from django.db import models
from django.contrib.auth.models import User

from .product import Product


class InventoryCheck(models.Model):
    """
    Inventory check model for managing inventory check tasks.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='Check Name')
    description = models.TextField(blank=True, verbose_name='Description')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Status')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inventory_checks_created', verbose_name='Created By')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, 
        related_name='inventory_checks_approved', 
        null=True, blank=True,
        verbose_name='Approved By'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Approved At')
    
    class Meta:
        verbose_name = 'Inventory Check'
        verbose_name_plural = 'Inventory Checks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} - {self.get_status_display()}'


class InventoryCheckItem(models.Model):
    """
    Inventory check item that records the check result for each product.
    """
    inventory_check = models.ForeignKey(InventoryCheck, on_delete=models.CASCADE, related_name='items', verbose_name='Inventory Check')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Product')
    system_quantity = models.IntegerField(verbose_name='System Quantity')
    actual_quantity = models.IntegerField(null=True, blank=True, verbose_name='Actual Quantity')
    difference = models.IntegerField(null=True, blank=True, verbose_name='Difference')
    notes = models.TextField(blank=True, verbose_name='Notes')
    checked_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Checked By')
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name='Checked At')
    
    class Meta:
        verbose_name = 'Inventory Check Item'
        verbose_name_plural = 'Inventory Check Items'
        unique_together = ('inventory_check', 'product')
    
    def __str__(self):
        return f'{self.product.name} - System:{self.system_quantity} Actual:{self.actual_quantity or "Not checked"}'
    
    def save(self, *args, **kwargs):
        # Calculate difference when actual quantity is set
        if self.actual_quantity is not None:
            self.difference = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs) 