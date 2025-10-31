from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

# Explicitly import models
import inventory.models
from .models.common import OperationLog 
from . import forms
from .ali_barcode_service import AliBarcodeService

@login_required
def barcode_product_create(request):
    """
    View for querying product info by barcode and creating products
    Supports GET barcode lookup and POST save
    Checks DB first, then API if not found
    """
    barcode = request.GET.get('barcode', '')
    barcode_data = None
    initial_data = {}
    
    # If barcode given, try lookup
    if barcode:
        # First check DB for existing product with barcode
        try:
            existing_product = inventory.models.Product.objects.get(barcode=barcode)
            messages.warning(request, f'Product with barcode {barcode} already exists, do not add duplicates')
            return redirect('product_list')
        except inventory.models.Product.DoesNotExist:
            # Use Aliyun barcode service to query product info
            barcode_data = AliBarcodeService.search_barcode(barcode)
            
            if barcode_data:
                # Pre-fill form data
                initial_data = {
                    'barcode': barcode,
                    'name': barcode_data.get('name', ''),
                    'specification': barcode_data.get('specification', ''),
                    'manufacturer': barcode_data.get('manufacturer', ''),
                    'price': barcode_data.get('suggested_price', 0),
                    'cost': barcode_data.get('suggested_price', 0) * 0.8 if barcode_data.get('suggested_price') else 0,  # Default cost is 80% of suggest price
                    'description': barcode_data.get('description', ''),
                    'is_active': True
                }
                # Try to look up matching category in DB
                category_name = barcode_data.get('category', '')
                if category_name:
                    try:
                        category = inventory.models.Category.objects.filter(name__icontains=category_name).first()
                        if category:
                            initial_data['category'] = category.id
                    except Exception as e:
                        print(f"Error finding category: {e}")
                        # Keeps going for other fields
                messages.success(request, 'Fetched product info successfully, please confirm and complete details')
            else:
                messages.info(request, f'No product info found for barcode {barcode}, please enter by hand')
                initial_data = {'barcode': barcode, 'is_active': True}
    # Form post
    if request.method == 'POST':
        form = forms.ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.is_active = True
            product.save()
            # Create initial inventory record
            initial_stock = request.POST.get('initial_stock', 0)
            try:
                initial_stock = int(initial_stock)
                if initial_stock < 0:
                    initial_stock = 0
            except ValueError:
                initial_stock = 0
            # Check for existing inventory record
            inventory_record, created = inventory.models.Inventory.objects.get_or_create(
                product=product,
                defaults={'quantity': initial_stock}
            )
            # If already exists, update quantity
            if not created:
                inventory_record.quantity += initial_stock
                inventory_record.save()
            # Log operation
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Added new product: {product.name} (barcode: {product.barcode}), initial stock: {initial_stock}',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(product)
            )
            messages.success(request, 'Product added successfully')
            return redirect('product_list')
    else:
        form = forms.ProductForm(initial=initial_data)
    # Ensure barcode_data is a dict if None
    if barcode_data is None:
        barcode_data = {}
    # Render template
    return render(request, 'inventory/barcode_product_form.html', {
        'form': form,
        'barcode': barcode,
        'barcode_data': barcode_data
    })

@login_required
def barcode_lookup(request):
    """
    AJAX endpoint for barcode info lookup
    Checks DB, then calls API if not found
    """
    barcode = request.GET.get('barcode', '')
    if not barcode:
        return JsonResponse({'success': False, 'message': 'Please provide barcode'})
    # Check DB
    try:
        product = inventory.models.Product.objects.get(barcode=barcode)
        return JsonResponse({
            'success': True,
            'exists': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'specification': product.specification,
            'manufacturer': product.manufacturer,
            'description': product.description,
            'message': 'Product already exists in the system'
        })
    except inventory.models.Product.DoesNotExist:
        # Call Aliyun barcode service
        barcode_data = AliBarcodeService.search_barcode(barcode)
        if barcode_data:
            return JsonResponse({
                'success': True,
                'exists': False,
                'data': barcode_data,
                'message': 'Fetched product info successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'exists': False,
                'message': 'No product info found'
            })