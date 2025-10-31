"""Utility functions package providing various helpers."""

from .date_utils import get_month_range, get_quarter_range, get_year_range, get_date_range
from .csv_utils import validate_csv, validate_csv_data
from .logging import log_operation
from .query_utils import get_paginated_queryset, build_filter_query
from .view_utils import require_ajax, require_post, get_referer_url, get_int_param
from .image_utils import generate_thumbnail, save_thumbnail, image_to_base64, resize_image, get_image_dimensions
import qrcode  # Add qrcode import

# Try importing functions from barcode_utils; fall back to barcode_api alternatives on failure
try:
    from .barcode_utils import generate_product_barcode, generate_batch_barcode, generate_qrcode
except ImportError:
    from .barcode_api import generate_product_barcode_alt as generate_product_barcode
    from .barcode_api import generate_batch_barcode_alt as generate_batch_barcode
    # Use the basic qrcode library as a fallback
    def generate_qrcode(content, size=10, box_size=10, border=4):
        qr = qrcode.QRCode(
            version=size,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(content)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

__all__ = [
    # Date utilities
    'get_month_range', 'get_quarter_range', 'get_year_range', 'get_date_range',
    
    # CSV utilities
    'validate_csv', 'validate_csv_data',
    
    # Logging utilities
    'log_operation',
    
    # Query utilities
    'get_paginated_queryset', 'build_filter_query',
    
    # View utilities
    'require_ajax', 'require_post', 'get_referer_url', 'get_int_param',
    
    # Image utilities
    'generate_thumbnail', 'save_thumbnail', 'image_to_base64', 'resize_image', 'get_image_dimensions',
    
    # Barcode utilities
    'generate_product_barcode', 'generate_batch_barcode', 'generate_qrcode',
] 