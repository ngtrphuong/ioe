"""
Barcode generation utility functions
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont
import qrcode
import barcode
from barcode.writer import ImageWriter
from decimal import Decimal


def generate_product_barcode(product, price=None, barcode_type='ean13'):
    """
    Generate a product barcode image.
    
    Args:
        product: Product object
        price: Displayed price; if None, use product's default retail price
        barcode_type: Barcode type, supports 'ean13', 'code128', etc.
        
    Returns:
        PIL.Image: Barcode image
    """
    if not price:
        price = product.retail_price
    
    # Get barcode content
    barcode_content = product.barcode
    if not barcode_content:
        # If product has no barcode, use product ID
        barcode_content = f"ID{product.id:08d}"
    
    # Determine barcode type
    if barcode_type == 'ean13' and len(barcode_content) != 13:
        # If EAN13 is required but not 13 digits, switch to CODE128
        barcode_type = 'code128'
    
    try:
        # Generate barcode
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_image = barcode_class(barcode_content, writer=ImageWriter())
        
        # Render barcode
        barcode_img = barcode_image.render(
            writer_options={
                'module_width': 0.6,
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 1.0,
                'quiet_zone': 6.0
            }
        )
        
        # Create full image containing product info
        width, height = barcode_img.size
        new_height = height + 100  # Extra space for product info
        
        # Create new image
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # Add product info
        draw = ImageDraw.Draw(complete_img)
        
        # Try to load font; fallback to default
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')  # Microsoft YaHei
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # Use default font
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # Product name (truncate if too long)
        product_name = product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # Render info
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"Price: VNĐ{price:.2f}", fill='black', font=info_font)
        draw.text((10, height + 70), f"Specification: {product.specification or 'Standard'}", fill='black', font=info_font)
        
        return complete_img
        
    except (ValueError, AttributeError) as e:
        # Default image on error
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"Barcode generation error: {str(e)}", fill='black')
        draw.text((10, 30), f"Product: {product.name}", fill='black')
        draw.text((10, 50), f"Barcode: {barcode_content}", fill='black')
        return error_img


def generate_batch_barcode(batch, barcode_type='code128'):
    """
    Generate a batch barcode image.
    
    Args:
        batch: Batch object
        barcode_type: Barcode type
        
    Returns:
        PIL.Image: Barcode image
    """
    # Generate batch code barcode
    batch_code = f"B{batch.id:06d}"
    
    try:
        # Generate barcode
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_image = barcode_class(batch_code, writer=ImageWriter())
        
        # Render barcode
        barcode_img = barcode_image.render(
            writer_options={
                'module_width': 0.6,
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 1.0,
                'quiet_zone': 6.0
            }
        )
        
        # Create full image containing batch info
        width, height = barcode_img.size
        new_height = height + 100  # Extra space for batch info
        
        # Create new image
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # Add batch info
        draw = ImageDraw.Draw(complete_img)
        
        # Try to load font; fallback to default
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')  # Microsoft YaHei
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # Use default font
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # Product name (truncate if too long)
        product_name = batch.product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # Render info
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"Batch: {batch.batch_number}", fill='black', font=info_font)
        draw.text((10, height + 70), f"Production date: {batch.production_date.strftime('%Y-%m-%d')}", fill='black', font=info_font)
        
        return complete_img
        
    except (ValueError, AttributeError) as e:
        # Default image on error
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"Barcode generation error: {str(e)}", fill='black')
        draw.text((10, 30), f"Batch: {batch.batch_number}", fill='black')
        draw.text((10, 50), f"Product: {batch.product.name}", fill='black')
        return error_img


def generate_qrcode(content, size=10, box_size=10, border=4):
    """
    Generate a QR code image.
    
    Args:
        content: QR content
        size: QR code version (size)
        box_size: Pixel size of each box
        border: Border width
        
    Returns:
        PIL.Image: QR code image
    """
    qr = qrcode.QRCode(
        version=size,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    return img 