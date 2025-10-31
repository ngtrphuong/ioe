"""
Inventory management services.
"""
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F, Sum, Q
from django.contrib.contenttypes.models import ContentType

from inventory.models import (
    Product,
    Inventory,
    InventoryTransaction,
    Category
)
from inventory.exceptions import InsufficientStockError, InventoryValidationError
from inventory.utils.logging import log_exception, log_action

class InventoryService:
    """Service for inventory operations."""
    
    @staticmethod
    @log_exception
    def check_stock(product, quantity):
        """
        Check if there is sufficient stock for a product.
        
        Args:
            product: The product to check
            quantity: The quantity needed
            
        Returns:
            bool: True if there is sufficient stock, False otherwise
        """
        try:
            inventory = Inventory.objects.get(product=product)
            return inventory.quantity >= quantity
        except Inventory.DoesNotExist:
            return False
    
    @staticmethod
    @log_exception
    @transaction.atomic
    def update_stock(product, quantity, transaction_type, operator, notes=""):
        """
        Update stock level for a product.
        
        Args:
            product: The product to update
            quantity: The quantity to add (positive) or remove (negative)
            transaction_type: The type of transaction ('IN', 'OUT', 'ADJUST')
            operator: The user performing the operation
            notes: Notes about the transaction
            
        Returns:
            tuple: (inventory, transaction) - The updated inventory and the transaction record
        """
        # Validate inputs
        if not isinstance(operator, User):
            raise InventoryValidationError("Operator must be a valid user")
        
        if transaction_type not in ('IN', 'OUT', 'ADJUST'):
            raise InventoryValidationError("Invalid transaction type")
        
        # Get or create inventory
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            defaults={'quantity': 0, 'warning_level': 10}
        )
        
        # For outgoing transactions, check stock
        if transaction_type == 'OUT' and inventory.quantity < quantity:
            raise InsufficientStockError(
                f"Insufficient stock. Needed: {quantity}, Current Stock: {inventory.quantity}",
                extra={'product': product.name, 'current_stock': inventory.quantity, 'needed': quantity}
            )
        
        # Create transaction record
        transaction = InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=quantity,
            operator=operator,
            notes=notes
        )
        
        # Update inventory
        if transaction_type == 'IN':
            inventory.quantity = F('quantity') + quantity
        elif transaction_type == 'OUT':
            inventory.quantity = F('quantity') - quantity
        else:  # ADJUST
            inventory.quantity = quantity
        
        inventory.save()
        inventory.refresh_from_db()  # Refresh to get updated value
        
        # Log the action
        log_action(
            user=operator,
            operation_type='INVENTORY',
            details=f"{transaction_type} Transaction: {product.name}, Quantity: {quantity}, Notes: {notes}",
            related_object=transaction
        )
        
        # Check if stock is low and send notification if needed
        InventoryService.check_stock_level(inventory)
        
        return inventory, transaction
    
    @staticmethod
    @log_exception
    def check_stock_level(inventory):
        """
        Check if stock level is below warning level and send notification if needed.
        
        Args:
            inventory: The inventory to check
        """
        if inventory.quantity <= inventory.warning_level:
            # Log warning
            from inventory.models import OperationLog
            
            OperationLog.objects.create(
                operator=User.objects.filter(is_superuser=True).first(),
                operation_type='INVENTORY',
                details=f"Stock warning: {inventory.product.name} stock ({inventory.quantity}) is below the warning level ({inventory.warning_level})",
                related_object_id=inventory.id,
                related_content_type=ContentType.objects.get_for_model(inventory.__class__)
            )
            
            # Send email if configured
            if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
                try:
                    managers = User.objects.filter(
                        Q(is_superuser=True) | Q(groups__name='Store Manager') | Q(groups__name='Inventory Manager')
                    ).distinct()
                    
                    recipient_list = [
                        manager.email for manager in managers 
                        if manager.email
                    ]
                    
                    if recipient_list:
                        send_mail(
                            subject=f'Stock Warning: {inventory.product.name}',
                            message=f'''
                            Product: {inventory.product.name}
                            Current Stock: {inventory.quantity}
                            Warning Level: {inventory.warning_level}
                            Barcode: {inventory.product.barcode}
                            
                            Please replenish stock promptly.
                            ''',
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=recipient_list,
                            fail_silently=True
                        )
                except Exception as e:
                    # Just log the error but don't break the process
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending stock warning email: {str(e)}", exc_info=True)
    
    @staticmethod
    @log_exception
    def get_low_stock_items():
        """
        Get all inventory items that are below their warning level.
        
        Returns:
            QuerySet: Inventory items with low stock
        """
        return Inventory.objects.filter(
            quantity__lte=F('warning_level')
        ).select_related('product')
    
    @staticmethod
    @log_exception
    def get_inventory_value():
        """
        Calculate the total inventory value (cost * quantity).
        
        Returns:
            Decimal: Total inventory value
        """
        return Inventory.objects.annotate(
            value=F('quantity') * F('product__cost')
        ).aggregate(total_value=Sum('value'))['total_value'] or 0 