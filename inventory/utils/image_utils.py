"""
Image processing utility functions
"""
from io import BytesIO
from PIL import Image, ImageOps
import os


def generate_thumbnail(image_file, size=(300, 300), format='JPEG', quality=85):
    """
    Generate a thumbnail image.
    
    Args:
        image_file: Original image file (Django UploadedFile or file path)
        size: Thumbnail size as (width, height)
        format: Image format ('JPEG', 'PNG', etc.)
        quality: Image quality (1-100)
        
    Returns:
        PIL.Image: The processed thumbnail image
    """
    # If it's a file path, open the file
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # If it's a Django InMemoryUploadedFile or TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # Already a PIL.Image object
        img = image_file
    
    # Convert to RGB mode (remove alpha channel)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Generate thumbnail
    img.thumbnail(size, Image.Resampling.LANCZOS)
    
    # Ensure thumbnail is the specified size (by fitting)
    thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    
    return thumb


def save_thumbnail(image, path, format='JPEG', quality=85):
    """
    Save a thumbnail to the specified path.
    
    Args:
        image: PIL.Image object
        path: Target path to save
        format: Image format
        quality: Image quality
        
    Returns:
        str: The saved path
    """
    # Ensure directory exists
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Save image
    image.save(path, format=format, quality=quality)
    
    return path


def image_to_base64(image, format='JPEG', quality=85):
    """
    Convert an image to base64 data URI.
    
    Args:
        image: PIL.Image object
        format: Image format
        quality: Image quality
        
    Returns:
        str: Base64-encoded image data URI
    """
    import base64
    
    buffered = BytesIO()
    image.save(buffered, format=format, quality=quality)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return f"data:image/{format.lower()};base64,{img_str}"


def resize_image(image_file, size, format='JPEG', quality=85):
    """
    Resize an image.
    
    Args:
        image_file: Original image file or path
        size: New size as (width, height)
        format: Image format
        quality: Image quality
        
    Returns:
        PIL.Image: Resized image
    """
    # If it's a file path, open the file
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # If it's a Django InMemoryUploadedFile or TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # Already a PIL.Image object
        img = image_file
    
    # Convert to RGB mode (remove alpha channel)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize image
    resized_img = img.resize(size, Image.Resampling.LANCZOS)
    
    return resized_img


def get_image_dimensions(image_file):
    """
    Get image dimensions.
    
    Args:
        image_file: Image file object or path
        
    Returns:
        tuple: (width, height)
    """
    # If it's a file path, open the file
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # If it's a Django InMemoryUploadedFile or TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # Already a PIL.Image object
        img = image_file
    
    return img.size 