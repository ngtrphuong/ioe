# Import all models from respective modules

# Product models
from .product import Product, Category, Color, Size, Store, ProductImage, ProductBatch, Supplier

# Inventory models
from .inventory import (
    Inventory, InventoryTransaction, 
    check_inventory, update_inventory, StockAlert
)

# Inventory check models
from .inventory_check import InventoryCheck, InventoryCheckItem

# Member models
from .member import Member, MemberLevel, RechargeRecord, MemberTransaction

# Sales models
from .sales import Sale, SaleItem

# Common models
from .common import OperationLog, SystemConfig

# Export all models to make them accessible via inventory.models
__all__ = [
    # Product models
    'Product', 'Category', 'Color', 'Size', 'Store', 'ProductImage', 'ProductBatch', 'Supplier', 'Category',
    
    # Inventory models
    'Inventory', 'InventoryTransaction', 'check_inventory', 
    'update_inventory', 'StockAlert',
    
    # Inventory check models
    'InventoryCheck', 'InventoryCheckItem',
    
    # Member models
    'Member', 'MemberLevel', 'RechargeRecord', 'MemberTransaction',
    
    # Sales models
    'Sale', 'SaleItem',
    
    # Common models
    'OperationLog', 'SystemConfig',
] 