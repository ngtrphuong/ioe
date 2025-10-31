from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import Inventory, InventoryTransaction

def update_inventory(product, quantity, transaction_type, operator, notes=''):
    """
    Update product inventory
    :param product: Product object
    :param quantity: Amount (positive for stock in, negative for stock out)
    :param transaction_type: Transaction type ('IN'/'OUT'/'ADJUST')
    :param operator: Operator
    :param notes: Notes
    """
    with transaction.atomic():
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            defaults={'quantity': 0, 'warning_level': 10}
        )
        # Check if inventory is sufficient (stock out only)
        if quantity < 0 and inventory.quantity + quantity < 0:
            raise ValidationError('Insufficient inventory')
        # Update inventory
        inventory.quantity += quantity
        inventory.save()
        # Create inventory transaction record
        InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=abs(quantity),  # Save absolute value
            operator=operator,
            notes=notes
        )

def check_inventory(product, quantity):
    """
    Check if product inventory is sufficient
    :param product: Product object
    :param quantity: Required amount
    :return: bool
    """
    try:
        inventory = Inventory.objects.get(product=product)
        return inventory.quantity >= quantity
    except Inventory.DoesNotExist:
        return False