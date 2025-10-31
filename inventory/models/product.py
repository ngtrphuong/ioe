from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Category Name')
    description = models.TextField(blank=True, verbose_name='Category Description')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    COLOR_CHOICES = [
        ('', 'No Color'),
        ('black', 'Black'),
        ('white', 'White'),
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('purple', 'Purple'),
        ('grey', 'Grey'),
        ('pink', 'Pink'),
        ('orange', 'Orange'),
        ('brown', 'Brown'),
        ('other', 'Other')
    ]
    
    SIZE_CHOICES = [
        ('', 'No Size'),
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
        ('XXXL', 'XXXL'),
        ('35', '35'),
        ('36', '36'),
        ('37', '37'),
        ('38', '38'),
        ('39', '39'),
        ('40', '40'),
        ('41', '41'),
        ('42', '42'),
        ('43', '43'),
        ('44', '44'),
        ('45', '45'),
        ('other', 'Other')
    ]
    
    barcode = models.CharField(max_length=100, unique=True, verbose_name='Product Barcode')
    name = models.CharField(max_length=200, verbose_name='Product Name')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Product Category')
    description = models.TextField(blank=True, verbose_name='Product Description')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Selling Price')
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cost Price')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Product Image')
    # Additional fields
    specification = models.CharField(max_length=200, blank=True, verbose_name='Specification')
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name='Manufacturer')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True, default='', verbose_name='Color')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True, default='', verbose_name='Size')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    def clean(self):
        if self.price < 0:
            raise ValidationError('Selling price cannot be negative')
        if self.cost < 0:
            raise ValidationError('Cost price cannot be negative')
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Color Name')
    code = models.CharField(max_length=20, blank=True, verbose_name='Color Code')
    
    class Meta:
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'
    
    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Size Name')
    
    class Meta:
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'
    
    def __str__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=100, verbose_name='Store Name')
    address = models.CharField(max_length=255, blank=True, verbose_name='Address')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Phone Number')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    class Meta:
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Product Image Model"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, verbose_name='Product')
    image = models.ImageField(upload_to='products/', verbose_name='Image')
    thumbnail = models.CharField(max_length=255, blank=True, null=True, verbose_name='Thumbnail Path')
    alt_text = models.CharField(max_length=255, blank=True, verbose_name='Alt Text')
    order = models.IntegerField(default=0, verbose_name='Order')
    is_primary = models.BooleanField(default=False, verbose_name='Is Primary Image')
    
    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.id}"
    
    def save(self, *args, **kwargs):
        # If marked as primary, ensure other images are not primary
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super(ProductImage, self).save(*args, **kwargs)


class ProductBatch(models.Model):
    """Product Batch Model"""
    product = models.ForeignKey(Product, related_name='batches', on_delete=models.CASCADE, verbose_name='Product')
    batch_number = models.CharField(max_length=100, verbose_name='Batch Number')
    production_date = models.DateField(null=True, blank=True, verbose_name='Production Date')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='Expiry Date')
    quantity = models.IntegerField(default=0, verbose_name='Quantity')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Cost Price')
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Supplier')
    remarks = models.TextField(blank=True, verbose_name='Remarks')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='created_batches', verbose_name='Created By')
    
    class Meta:
        verbose_name = 'Product Batch'
        verbose_name_plural = 'Product Batches'
        unique_together = ('product', 'batch_number')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"


class Supplier(models.Model):
    """Supplier Model"""
    name = models.CharField(max_length=100, verbose_name='Supplier Name')
    contact_person = models.CharField(max_length=50, blank=True, verbose_name='Contact Person')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Phone Number')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.TextField(blank=True, verbose_name='Address')
    remarks = models.TextField(blank=True, verbose_name='Remarks')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
    
    def __str__(self):
        return self.name 