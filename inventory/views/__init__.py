# Import member-related views
from .member import (
    member_search_by_phone,
    member_list,
    member_detail,
    member_create,
    member_update,
    member_delete,
    member_edit,  # Alias function for compatibility
    member_details,  # Alias function for compatibility
    member_add_ajax,
    member_level_list,
    member_level_create,
    member_level_update,
    member_level_edit,  # Alias function for compatibility
    member_level_delete,
    member_import,
    member_export,
    member_points_adjust,
    member_recharge,
    member_recharge_records,
    member_balance_adjust
)

# Import product-related views
from .product import (
    product_list,
    product_create,
    product_edit,
    product_update,
    product_detail,
    product_delete,
    product_category_list,
    product_category_create,
    product_category_update,
    product_category_delete,
    product_batch_create,
    product_batch_update,
    product_bulk_create,
    product_import,
    product_export
)

# Import barcode-related views
from .barcode import (
    barcode_lookup,
    barcode_scan,
    barcode_product_create,
    product_by_barcode,
    scan_barcode,
    get_product_batches,
    # The following features are deprecated but API compatibility is maintained
    generate_barcode_view,
    batch_barcode_view,
    bulk_barcode_generation,
    barcode_template
)

# Import core views
from .core import (
    index,
    reports_index
)

# Import inventory-related views
from .inventory import (
    inventory_list,
    inventory_transaction_list,
    inventory_in,
    inventory_out,
    inventory_adjust,
    inventory_transaction_create,
)

# Import report-related views
from .report import (
    sales_report,
    inventory_report,
    member_report,
    product_performance_report,
    daily_summary_report,
    custom_report,
    profit_analysis,
    inventory_batch_report
)

# Import system-related views
from .system import (
    system_settings,
    store_settings,
    store_list,
    delete_store,
    system_info,
    system_maintenance,
)

# Import sales-related views
from .sales import (
    sale_list,
    sale_detail,
    sale_create,
    sale_item_create,
    sale_complete,
    sale_cancel,
    sale_delete_item,
    member_purchases,
    birthday_members_report,
)

# Wildcard imports removed to avoid circular imports
# from inventory.views.barcode import *
# Add other view module imports as needed
# from inventory.views.product import *
# from inventory.views.inventory import *
# from inventory.views.inventory_check import *
# from inventory.views.member import *
# from inventory.views.report import *
# from inventory.views.system import * 