"""
Barcode generation utility functions - custom implementation not dependent on the barcode library
"""
import io
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
import qrcode
from decimal import Decimal


def draw_code128_barcode(text, height=100, thickness=3, quiet_zone=10):
    """
    Simple Code 128 barcode drawing implementation.

    Args:
        text: Barcode text
        height: Barcode height
        thickness: Barcode line thickness
        quiet_zone: Quiet zone spacing on both sides

    Returns:
        PIL.Image: Barcode image
    """
    # Since barcode library is unavailable, simulate barcode with black rectangles
    # For real projects, use a professional library or implement complete Code 128 algorithm here
    
    # Create a white image
    width = len(text) * 10 * thickness + 2 * quiet_zone
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw alternating black stripes in the middle of the quiet zone
    x = quiet_zone
    for char in text:
        # Calculate barcode stripe width based on character ASCII value (simulated)
        stripe_width = (ord(char) % 3 + 1) * thickness
        
        # Draw a black stripe
        draw.rectangle([(x, 0), (x + stripe_width, height)], fill='black')
        x += stripe_width + thickness  # Space between the stripes
    
    # Try loading font
    try:
        font_path = os.path.join('static', 'fonts', 'msyh.ttf')
        font = ImageFont.truetype(font_path, 12)
    except IOError:
        font = ImageFont.load_default()
    
    # Display text below the barcode
    text_width = draw.textlength(text, font=font)
    draw.text(((width - text_width) / 2, height - 15), text, fill='black', font=font)
    
    return img


def generate_product_barcode_alt(product, price=None):
    """
    Generate product barcode image (alternative implementation)

    Args:
        product: Product object
        price: Displayed price

    Returns:
        PIL.Image: Barcode image object
    """
    if not price:
        price = product.retail_price
    
    # Get barcode content
    barcode_content = product.barcode
    if not barcode_content:
        # If product has no barcode, use product ID as barcode
        barcode_content = f"ID{product.id:08d}"
    
    try:
        # Generate barcode
        barcode_img = draw_code128_barcode(barcode_content, height=80)
        
        # Create a complete image with product info
        width, height = barcode_img.size
        new_height = height + 100  # Add extra space to show product info
        
        # Create new image
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # Add product info
        draw = ImageDraw.Draw(complete_img)
        
        # Try to load font
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # Use default font
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # Draw product name
        product_name = product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # Draw info/details
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"Price: VNĐ{price:.2f}", fill='black', font=info_font)
        draw.text((10, height + 70), f"Specification: {product.specification or 'Standard'}", fill='black', font=info_font)
        
        return complete_img
        
    except Exception as e:
        # Create a default image when error occurs
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"Barcode generation error: {str(e)}", fill='black')
        draw.text((10, 30), f"Product: {product.name}", fill='black')
        draw.text((10, 50), f"Barcode: {barcode_content}", fill='black')
        return error_img


def generate_batch_barcode_alt(batch):
    """
    Generate batch barcode image (alternative implementation)

    Args:
        batch: Batch object

    Returns:
        PIL.Image: Barcode image object
    """
    # Generate batch code barcode
    batch_code = f"B{batch.id:06d}"
    
    try:
        # Generate barcode
        barcode_img = draw_code128_barcode(batch_code, height=80)
        
        # Create an image containing batch info
        width, height = barcode_img.size
        new_height = height + 100  # Add extra space to show batch info
        
        # Create new image
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # Add batch info
        draw = ImageDraw.Draw(complete_img)
        
        # Try to load font
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # Use default font
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # Draw batch info
        product_name = batch.product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # Draw info/details
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"Batch: {batch.batch_number}", fill='black', font=info_font)
        draw.text((10, height + 70), f"Production date: {batch.production_date.strftime('%Y-%m-%d')}", fill='black', font=info_font)
        
        return complete_img
        
    except Exception as e:
        # Create a default image when error occurs
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"Barcode generation error: {str(e)}", fill='black')
        draw.text((10, 30), f"Batch: {batch.batch_number}", fill='black')
        draw.text((10, 50), f"Product: {batch.product.name}", fill='black')
        return error_img 