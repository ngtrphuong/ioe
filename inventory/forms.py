# This is a transitional file for backward compatibility.
# Forms are now refactored into separate files under inventory/forms/.

# Import all forms from the refactored structure
from inventory.forms.product_forms import (
    ProductForm, CategoryForm
)

from inventory.forms.inventory_check_forms import (
    InventoryCheckForm, InventoryCheckItemForm, InventoryCheckApproveForm
)

from inventory.forms.member_forms import (
    MemberForm, MemberLevelForm, RechargeForm
)

from inventory.forms.inventory_forms import (
    InventoryTransactionForm
)

from inventory.forms.sales_forms import (
    SaleForm, SaleItemForm
)

from inventory.forms.report_forms import (
    DateRangeForm, TopProductsForm, InventoryTurnoverForm
)

from inventory.forms_batch import (
    BatchProductImportForm, BatchInventoryUpdateForm, ProductBatchDeleteForm
)

# WARNING: This file will be deleted after refactoring is complete.
# Please import forms directly from inventory.forms, e.g.:
# from inventory.forms import ProductForm