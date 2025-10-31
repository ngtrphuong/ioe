from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

# Explicitly import original models
import inventory.models
from inventory.models.common import OperationLog 
from inventory.forms import ProductForm  # Directly import the required form from forms package
from inventory.ali_barcode_service import AliBarcodeService
from inventory.services.product_service import search_products

# External barcode service API configuration (example, replace with your own API key)
BARCODE_API_APP_KEY = "your_app_key"
BARCODE_API_APP_SECRET = "your_app_secret"
BARCODE_API_URL = "https://api.example.com/barcode"

@login_required
def barcode_product_create(request):
    """
    View to fetch product info by barcode and create product.
    Supports GET for fetching by barcode, POST for saving product.
    Checks DB first; calls external API if not found.
    """
    barcode = request.GET.get('barcode', '')
    barcode_data = None
    initial_data = {}
    
    # If barcode is provided, try to fetch product info
    if barcode:
        # First check if a product with this barcode exists in the database
        try:
            existing_product = inventory.models.Product.objects.get(barcode=barcode)
            messages.warning(request, f'Product with barcode {barcode} already exists; do not add duplicate')
            return redirect('product_list')
        except inventory.models.Product.DoesNotExist:
            # Call Aliyun barcode service to fetch product info
            barcode_data = AliBarcodeService.search_barcode(barcode)
            
            if barcode_data:
                # Prefill form data
                initial_data = {
                    'barcode': barcode,
                    'name': barcode_data.get('name', ''),
                    'specification': barcode_data.get('specification', ''),
                    'manufacturer': barcode_data.get('manufacturer', ''),
                    'price': barcode_data.get('suggested_price', 0),
                    'cost': barcode_data.get('suggested_price', 0) * 0.8 if barcode_data.get('suggested_price') else 0,  # Default cost as 80% of suggested price
                    'description': barcode_data.get('description', '')
                }
                
                # Try to find matching product category from DB
                category_name = barcode_data.get('category', '')
                if category_name:
                    try:
                        category = inventory.models.Category.objects.filter(name__icontains=category_name).first()
                        if category:
                            initial_data['category'] = category.id
                    except Exception as e:
                        print(f"Error finding product category: {e}")
                        # Error handling, but does not affect other form fields
                messages.success(request, 'Successfully fetched product info, please confirm and complete details')
            else:
                messages.info(request, f'Product info not found for barcode {barcode}, please fill in manually')
                initial_data = {'barcode': barcode}
    
    # Handle form submission
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Save product info
            product = form.save()
            
            # Create initial inventory record
            initial_stock = request.POST.get('initial_stock', 0)
            try:
                initial_stock = int(initial_stock)
                if initial_stock < 0:
                    initial_stock = 0
            except ValueError:
                initial_stock = 0
                
            # Check if product inventory already exists
            inventory, created = inventory.models.Inventory.objects.get_or_create(
                product=product,
                defaults={'quantity': initial_stock}
            )
            
            # Update quantity if inventory record already exists
            if not created:
                inventory.quantity += initial_stock
                inventory.save()
            
            # Record operation log
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Added new product: {product.name} (Barcode: {product.barcode}), initial stock: {initial_stock}',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(product)
            )
            
            messages.success(request, 'Product successfully added')
            return redirect('product_list')
    else:
        form = ProductForm(initial=initial_data)
    
    # Render template
    return render(request, 'inventory/barcode_product_form.html', {
        'form': form,
        'barcode': barcode,
        'barcode_data': barcode_data
    })

@login_required
def barcode_lookup(request):
    """
    AJAX endpoint for barcode lookup.
    Checks database first, then external API if not found.
    """
    barcode = request.GET.get('barcode', '')
    if not barcode:
        return JsonResponse({'success': False, 'message': 'Please provide a barcode'})
        
    # First check if a product with this barcode already exists in the database
    try:
        product = inventory.models.Product.objects.get(barcode=barcode)
        # Get inventory info
        try:
            inventory = inventory.models.Inventory.objects.get(product=product)
            stock = inventory.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'exists': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer,
            'description': product.description,
            'message': 'Product already exists in the system'
        })
    except inventory.models.Product.DoesNotExist:
        # Call Aliyun barcode service to get product info
        barcode_data = AliBarcodeService.search_barcode(barcode)
        
        if barcode_data:
            return JsonResponse({
                'success': True,
                'exists': False,
                'data': barcode_data,
                'message': 'Successfully got product info'
            })
        else:
            return JsonResponse({
                'success': False,
                'exists': False,
                'message': 'Product information not found'
            })

@login_required
def barcode_scan(request):
    """Barcode scan page, used for testing barcode functionality"""
    return render(request, 'inventory/barcode/barcode_scan.html')

def product_by_barcode(request, barcode):
    """API to get product info by barcode"""
    try:
        # First try an exact barcode match
        product = inventory.models.Product.objects.get(barcode=barcode)
        # Get inventory info
        try:
            inventory_obj = inventory.models.Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except inventory.models.Product.DoesNotExist:
        # If no exact match, try partial/fuzzy match with barcode or name
        products = inventory.models.Product.objects.filter(
            Q(barcode__icontains=barcode) | 
            Q(name__icontains=barcode)
        ).order_by('name')[:5]  # Limit number of results returned
        
        if products.exists():
            # If only one result found
            if products.count() == 1:
                product = products.first()
                # Get inventory info
                try:
                    inventory_obj = inventory.models.Inventory.objects.get(product=product)
                    stock = inventory_obj.quantity
                except inventory.models.Inventory.DoesNotExist:
                    stock = 0
                    
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'product_id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'stock': stock,
                    'category': product.category.name if product.category else '',
                    'specification': product.specification,
                    'manufacturer': product.manufacturer
                })
            # If multiple results found
            else:
                product_list = []
                for product in products:
                    try:
                        inventory_obj = inventory.models.Inventory.objects.get(product=product)
                        stock = inventory_obj.quantity
                    except inventory.models.Inventory.DoesNotExist:
                        stock = 0
                        
                    product_list.append({
                        'product_id': product.id,
                        'name': product.name,
                        'price': float(product.price),
                        'barcode': product.barcode,
                        'stock': stock,
                        'category': product.category.name if product.category else ''
                    })
                    
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'products': product_list
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Product not found'
            })

@login_required
def scan_barcode(request):
    """Barcode scan functionality view"""
    if request.method == 'POST':
        barcode_data = request.POST.get('barcode_data')
        
        if not barcode_data:
            return JsonResponse({'error': 'No barcode data provided'}, status=400)
        
        # Try to find product
        try:
            # If it is a product barcode (typically starts with product ID)
            if barcode_data.startswith('P'):
                product_id = barcode_data.split('-')[0][1:]
                product = get_object_or_404(inventory.models.Product, pk=product_id)
                
                return JsonResponse({
                    'type': 'product',
                    'data': {
                        'id': product.id,
                        'name': product.name,
                        'retail_price': float(product.retail_price),
                        'wholesale_price': float(product.wholesale_price),
                        'inventory': product.current_inventory,
                        'barcode': product.barcode or barcode_data,
                    }
                })
            
            # If it is a batch barcode (typically starts with B)
            elif barcode_data.startswith('B'):
                batch_id = barcode_data.split('-')[0][1:]
                batch = get_object_or_404(inventory.models.ProductBatch, pk=batch_id)
                
                return JsonResponse({
                    'type': 'batch',
                    'data': {
                        'id': batch.id,
                        'product': {
                            'id': batch.product.id,
                            'name': batch.product.name,
                            'retail_price': float(batch.product.retail_price),
                        },
                        'batch_number': batch.batch_number,
                        'manufacturing_date': batch.manufacturing_date.strftime('%Y-%m-%d') if batch.manufacturing_date else None,
                        'expiry_date': batch.expiry_date.strftime('%Y-%m-%d') if batch.expiry_date else None,
                        'remaining_quantity': batch.remaining_quantity,
                    }
                })
            
            # Otherwise, try to search by product barcode
            else:
                product = get_object_or_404(inventory.models.Product, barcode=barcode_data)
                
                return JsonResponse({
                    'type': 'product',
                    'data': {
                        'id': product.id,
                        'name': product.name,
                        'retail_price': float(product.retail_price),
                        'wholesale_price': float(product.wholesale_price),
                        'inventory': product.current_inventory,
                        'barcode': product.barcode,
                    }
                })
        
        except Exception as e:
            return JsonResponse({'error': f'Cannot find product or batch for this barcode: {str(e)}'}, status=404)
    
    # GET request
    return render(request, 'inventory/barcode/scan_barcode.html')

@login_required
def get_product_batches(request):
    """API view to get product batches"""
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'Missing product_id'}, status=400)
    
    try:
        batches = inventory.models.ProductBatch.objects.filter(
            product_id=product_id, 
            is_active=True,
            remaining_quantity__gt=0
        ).values('id', 'batch_number', 'manufacturing_date', 'expiry_date', 'remaining_quantity')
        
        return JsonResponse(list(batches), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# The following features for barcode generation/printing are deprecated
# Function definitions are retained for API compatibility but always return a 'feature disabled' message

@login_required
def generate_barcode_view(request, product_id=None):
    """Generate product barcode view - feature disabled"""
    messages.info(request, "Barcode generation is disabled because your products already have barcodes.")
    return redirect('product_list')  # Redirect to product list page

@login_required
def batch_barcode_view(request, batch_id=None):
    """Generate batch barcode view - feature disabled"""
    messages.info(request, "Batch barcode generation is disabled because your products already have barcodes.")
    return redirect('product_list')  # Redirect to product list page

@login_required
def bulk_barcode_generation(request):
    """Bulk barcode generation view - feature disabled"""
    messages.info(request, "Bulk barcode generation is disabled because your products already have barcodes.")
    return redirect('product_list')  # Redirect to product list page

@login_required
def barcode_template(request):
    """Barcode template settings view - feature disabled"""
    messages.info(request, "Barcode template settings are disabled because your products already have barcodes.")
    return redirect('product_list')  # Redirect to product list page

def product_search_api(request):
    """API to search products by name or other fields"""
    query = request.GET.get('query', '')
    if not query or len(query) < 2:  # Only search if at least 2 characters
        return JsonResponse({
            'success': False,
            'message': 'Please enter at least 2 characters to search'
        })
    
    # Use the service layer to search for products
    products = search_products(query, active_only=True)
    
    # Format output data
    result = []
    for product in products[:10]:  # Limit to 10 results
        try:
            inventory_obj = inventory.models.Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        result.append({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'barcode': product.barcode,
            'spec': product.specification,
            'category': product.category.name if product.category else ''
        })
    
    return JsonResponse({
        'success': True,
        'products': result,
        'count': len(result)
    })