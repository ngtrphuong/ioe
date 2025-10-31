# This is a transitional file for backward compatibility.
# Models are now refactored into separate files under inventory/models/.

# Import all models from the refactored model structure
from inventory.models.product import (
    Product, Category, Color, Size, Store
)

from inventory.models.inventory import (
    Inventory, InventoryTransaction, 
    check_inventory, update_inventory, StockAlert
)

from inventory.models.inventory_check import (
    InventoryCheck, InventoryCheckItem
)

from inventory.models.member import (
    Member, MemberLevel, RechargeRecord
)

from inventory.models.sales import (
    Sale, SaleItem
)

from inventory.models.common import (
    OperationLog
)

# WARNING: This file will be deleted after refactoring is complete.
# Please import models directly from inventory.models, e.g.:
# from inventory.models import Product