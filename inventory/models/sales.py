from django.db import models
from django.contrib.auth.models import User

from .product import Product
from .member import Member


class Sale(models.Model):
    """
    Sales Order Model
    """
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('wechat', 'WeChat'),
        ('alipay', 'Alipay'),
        ('card', 'Bank Card'),
        ('balance', 'Account Balance'),
        ('mixed', 'Mixed Payment'),
        ('other', 'Other')
    ]
    
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Member')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total Amount')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Discount Amount')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Final Amount')
    points_earned = models.IntegerField(default=0, verbose_name='Points Earned')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name='Payment Method')
    balance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Balance Paid')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Operator')
    remark = models.TextField(blank=True, verbose_name='Remarks')

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    def update_total_amount(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        return self.total_amount
    
    def save(self, *args, **kwargs):
        # Ensure total_amount is not None and is a valid value
        if self.total_amount is None:
            self.total_amount = 0
        
        if self.total_amount < self.discount_amount:
            self.discount_amount = self.total_amount
        
        self.final_amount = self.total_amount - self.discount_amount
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = 'Sales Order'
        verbose_name_plural = 'Sales Orders'

    def __str__(self):
        return f'Sales Order #{self.id} - {self.created_at.strftime("%Y-%m-%d %H:%M")}'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='items', verbose_name='Sales Order')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Product')
    quantity = models.IntegerField(verbose_name='Quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Standard Price')
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Actual Price')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than 0')
    
    def save(self, *args, **kwargs):
        # If actual price is not set, use standard price by default
        if self.actual_price is None:
            self.actual_price = self.price
            
        # Calculate subtotal
        self.subtotal = self.quantity * self.actual_price
        
        # Save SaleItem
        super().save(*args, **kwargs)
        
        # Update Sale total amount
        self.sale.update_total_amount()
        self.sale.save()
        
        # Update inventory
        from .inventory import update_inventory
        update_inventory(
            product=self.product,
            quantity=-self.quantity,  # Negative number means reduce inventory
            transaction_type='OUT',
            operator=self.sale.operator,
            notes=f'Sales Order #{self.sale.id}'
        )
    
    class Meta:
        verbose_name = 'Sales Item'
        verbose_name_plural = 'Sales Items'
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}' 