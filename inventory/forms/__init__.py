# Import all forms from individual form modules
from .product_forms import (
    ProductForm, CategoryForm, ProductBatchForm, 
    ProductImageFormSet, ProductBulkForm, ProductImportForm
)
from .inventory_check_forms import InventoryCheckForm, InventoryCheckItemForm, InventoryCheckApproveForm
from .member_forms import MemberForm, MemberLevelForm, RechargeForm, MemberImportForm
from .inventory_forms import InventoryTransactionForm
from .sales_forms import SaleForm, SaleItemForm
from .report_forms import (
    DateRangeForm, TopProductsForm, InventoryTurnoverForm,
    ReportFilterForm, SalesReportForm
)
from .system_forms import SystemConfigForm, StoreForm

# Set StoreForm's model
from django.apps import apps
try:
    Store = apps.get_model('inventory', 'Store')
    StoreForm._meta.model = Store
except:
    pass

# Continue importing from batch forms until full refactor
from inventory.forms_batch import (
    BatchProductImportForm, BatchInventoryUpdateForm, ProductBatchDeleteForm
)

# Export all forms for access via inventory.forms
__all__ = [
    # Product forms
    'ProductForm', 'CategoryForm', 'ProductBatchForm',
    'ProductImageFormSet', 'ProductBulkForm', 'ProductImportForm',
    # Inventory check forms
    'InventoryCheckForm', 'InventoryCheckItemForm', 'InventoryCheckApproveForm',
    # Member forms
    'MemberForm', 'MemberLevelForm', 'RechargeForm', 'MemberImportForm',
    # Inventory management form
    'InventoryTransactionForm',
    # Sales forms
    'SaleForm', 'SaleItemForm',
    # Report forms
    'DateRangeForm', 'TopProductsForm', 'InventoryTurnoverForm',
    'ReportFilterForm', 'SalesReportForm',
    # System config forms
    'SystemConfigForm', 'StoreForm',
    # Batch operation forms
    'BatchProductImportForm', 'BatchInventoryUpdateForm', 'ProductBatchDeleteForm',
]

# Future imports will go here as the refactor continues
# Example:
# from .inventory_forms import InventoryTransactionForm
# from .sales_forms import SaleForm, SaleItemForm 