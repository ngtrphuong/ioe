from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

import csv
import io
import base64
import uuid
import os
from PIL import Image
from datetime import datetime

from inventory.models import (
    Product, Category, ProductImage, ProductBatch,
    Inventory, Supplier
)
from inventory.forms import (
    ProductForm, CategoryForm, ProductBatchForm,
    ProductImageFormSet, ProductBulkForm, ProductImportForm
)
from inventory.utils import generate_thumbnail, validate_csv
from inventory.services import product_service


def product_by_barcode(request, barcode):
    """API to fetch product info by barcode"""
    try:
        # Try exact barcode match first
        product = Product.objects.get(barcode=barcode)
        # Get inventory info
        try:
            inventory_obj = Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except Product.DoesNotExist:
        # If exact match fails, try fuzzy match on barcode
        try:
            products = Product.objects.filter(barcode__icontains=barcode).order_by('barcode')[:5]
            
            if products.exists():
                # Return multiple matched products
                product_list = []
                for product in products:
                    try:
                        inventory_obj = Inventory.objects.get(product=product)
                        stock = inventory_obj.quantity
                    except Inventory.DoesNotExist:
                        stock = 0
                        
                    product_list.append({
                        'product_id': product.id,
                        'barcode': product.barcode,
                        'name': product.name,
                        'price': float(product.price),
                        'stock': stock
                    })
                    
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'products': product_list
                })
            else:
                return JsonResponse({'success': False, 'message': 'Product not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error during query: {str(e)}'})


@login_required
def product_list(request):
    """Product list view"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', 'active')  # Default to active products
    sort_by = request.GET.get('sort', 'updated')  # Default sort by updated time
    
    print(f"DEBUG: List filters - search: {search_query}, category: {category_id}, status: {status}, sort: {sort_by}")
    
    # Base queryset
    products = Product.objects.select_related('category').all()
    print(f"DEBUG: Initial queryset count: {products.count()}")
    
    # Apply filters
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(barcode__icontains=search_query) |
            Q(specification__icontains=search_query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Status filter
    if status == 'active':
        products = products.filter(is_active=True)
        print(f"DEBUG: Count after applying active status filter: {products.count()}")
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    # Sorting
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'price':
        products = products.order_by('price')
    elif sort_by == 'category':
        products = products.order_by('category__name', 'name')
    elif sort_by == 'created':
        products = products.order_by('-created_at')
    elif sort_by == 'updated':  # Sort by updated time
        products = products.order_by('-updated_at')
    else:  # Default to updated time descending
        products = products.order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(products, 15)  # 15 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get category list for filtering
    categories = Category.objects.all().order_by('name')
    
    # Calculate statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    
    print(f"DEBUG: Totals - products: {total_products}, active: {active_products}, current page count: {len(page_obj)}")
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_status': status,
        'sort_by': sort_by,
        'total_products': total_products,
        'active_products': active_products,
        'products': page_obj,
    }
    
    return render(request, 'inventory/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Product detail view"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get product inventory info
    try:
        inventory = Inventory.objects.get(product=product)
    except Inventory.DoesNotExist:
        inventory = None
    
    # Get product batch info
    batches = ProductBatch.objects.filter(product=product).order_by('-created_at')
    
    # Get product images
    images = ProductImage.objects.filter(product=product).order_by('order')
    
    # Get sales history
    from inventory.models import SaleItem
    sales_history = SaleItem.objects.filter(product=product).order_by('-sale__created_at')[:10]
    
    context = {
        'product': product,
        'inventory': inventory,
        'batches': batches,
        'images': images,
        'sales_history': sales_history,
    }
    
    return render(request, 'inventory/product/product_detail.html', context)


@login_required
def product_create(request):
    """Create product view"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images')
        
        # Validate only main form; image formset optional
        if form.is_valid():
            # Save product data
            product = form.save(commit=False)
            product.created_by = request.user
            product.is_active = True  # Ensure product is active by default
            product.save()
            
            # Process images only if image formset is valid
            if image_formset.is_valid():
                # Save product image
                for image_form in image_formset:
                    if image_form.cleaned_data and not image_form.cleaned_data.get('DELETE'):
                        image = image_form.save(commit=False)
                        image.product = product
                        
                        # Process image file
                        if image.image:
                            # Generate thumbnail
                            thumbnail = generate_thumbnail(image.image, (300, 300))
                            
                            # Save thumbnail
                            thumb_name = f'thumb_{uuid.uuid4()}.jpg'
                            thumb_path = f'products/thumbnails/{thumb_name}'
                            thumb_file = io.BytesIO()
                            thumbnail.save(thumb_file, format='JPEG')
                            
                            # Set thumbnail path
                            image.thumbnail = thumb_path
                        
                        image.save()
            
            # Create initial inventory record
            warning_level = 10  # Set a default warning level
            if 'warning_level' in form.cleaned_data and form.cleaned_data['warning_level'] is not None:
                warning_level = form.cleaned_data['warning_level']
                
            Inventory.objects.create(
                product=product,
                quantity=0,
                warning_level=warning_level
            )
            
            messages.success(request, f'Product {product.name} created successfully')
            
            # If coming from bulk page, return to bulk page
            if 'next' in request.POST and request.POST['next'] == 'bulk':
                return redirect('product_bulk_create')
            
            # Adjust redirect to avoid missing template issues
            return redirect('product_list')
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet(prefix='images')
        
        # If a category parameter is provided, set initial value
        category_id = request.GET.get('category')
        if category_id:
            try:
                form.fields['category'].initial = int(category_id)
            except (ValueError, TypeError):
                pass
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'title': 'Create Product',
        'submit_text': 'Save Product',
        'next': request.GET.get('next', '')
    }
    
    return render(request, 'inventory/product/product_form.html', context)


@login_required
def product_update(request, pk):
    """Update product view"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images', instance=product)
        
        # Validate only main form; image formset optional
        if form.is_valid():
            # Save product data
            product = form.save(commit=False)
            product.updated_at = timezone.now()
            product.updated_by = request.user
            product.save()
            
            # Process images only if image formset is valid
            if image_formset.is_valid():
                # Save product image
                for image_form in image_formset:
                    if image_form.cleaned_data:
                        if image_form.cleaned_data.get('DELETE'):
                            if image_form.instance.pk:
                                image_form.instance.delete()
                        else:
                            image = image_form.save(commit=False)
                            image.product = product
                            
                            # Process image file
                            if image.image and not image.thumbnail:
                                # Generate thumbnail
                                thumbnail = generate_thumbnail(image.image, (300, 300))
                                
                                # Save thumbnail
                                thumb_name = f'thumb_{uuid.uuid4()}.jpg'
                                thumb_path = f'products/thumbnails/{thumb_name}'
                                thumb_file = io.BytesIO()
                                thumbnail.save(thumb_file, format='JPEG')
                                
                                # Set thumbnail path
                                image.thumbnail = thumb_path
                            
                            image.save()
            
            # Update inventory warning level
            warning_level = 10  # Set a default warning level
            if 'warning_level' in form.cleaned_data and form.cleaned_data['warning_level'] is not None:
                warning_level = form.cleaned_data['warning_level']
                
            try:
                inventory = Inventory.objects.get(product=product)
                inventory.warning_level = warning_level
                inventory.save()
            except Inventory.DoesNotExist:
                Inventory.objects.create(
                    product=product,
                    quantity=0,
                    warning_level=warning_level
                )
            
            messages.success(request, f'Product {product.name} updated successfully')
            # Adjust redirect to avoid missing template issues
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
        # Set inventory warning level
        try:
            inventory = Inventory.objects.get(product=product)
            form.fields['warning_level'].initial = inventory.warning_level
        except Inventory.DoesNotExist:
            pass
        
        image_formset = ProductImageFormSet(prefix='images', instance=product)
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'product': product,
        'title': f'Edit Product: {product.name}',
        'submit_text': 'Update Product'
    }
    
    return render(request, 'inventory/product/product_form.html', context)


@login_required
def product_delete(request, pk):
    """Delete product view"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        
        # Mark as inactive instead of actual deletion
        product.is_active = False
        product.updated_at = timezone.now()
        product.updated_by = request.user
        product.save()
        
        messages.success(request, f'Product {product_name} marked as inactive')
        return redirect('product_list')
    
    return render(request, 'inventory/product/product_confirm_delete.html', {
        'product': product
    })


@login_required
def product_category_list(request):
    """Product category list view"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    # Base queryset
    categories = Category.objects.all()
    
    # Apply filters
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)
    
    # Add product count
    categories = categories.annotate(product_count=Count('product'))
    
    # Sorting
    categories = categories.order_by('name')
    
    # Calculate statistics
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(is_active=True).count()
    
    context = {
        'categories': categories,
        'search_query': search_query,
        'selected_status': status,
        'total_categories': total_categories,
        'active_categories': active_categories,
    }
    
    return render(request, 'inventory/product/category_list.html', context)


@login_required
def product_category_create(request):
    """Create product category view"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} created successfully')
            return redirect('product_category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Create Product Category',
        'submit_text': 'Save Category'
    }
    
    return render(request, 'inventory/product/category_form.html', context)


@login_required
def product_category_update(request, pk):
    """Update product category view"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} updated successfully')
            return redirect('product_category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}',
        'submit_text': 'Update Category'
    }
    
    return render(request, 'inventory/product/category_form.html', context)


@login_required
def product_category_delete(request, pk):
    """Delete product category view"""
    category = get_object_or_404(Category, pk=pk)
    
    # Check if category has related products
    product_count = Product.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if product_count > 0 and not request.POST.get('force_delete'):
            messages.error(request, f'Cannot delete category {category.name} with {product_count} products')
            return redirect('product_category_list')
        
        category_name = category.name
        
        if product_count > 0:
            # Set related products' category to None
            Product.objects.filter(category=category).update(category=None)
        
        # Mark as inactive instead of actual deletion
        category.is_active = False
        category.save()
        
        messages.success(request, f'Category {category_name} marked as inactive')
        return redirect('product_category_list')
    
    context = {
        'category': category,
        'product_count': product_count
    }
    
    return render(request, 'inventory/product/category_confirm_delete.html', context)


@login_required
def product_batch_create(request, product_id):
    """Create product batch view"""
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        form = ProductBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.product = product
            batch.created_by = request.user
            batch.save()
            
            messages.success(request, f'Batch {batch.batch_number} created successfully')
            return redirect('product_detail', pk=product.id)
    else:
        # Generate a default batch number
        current_date = datetime.now().strftime('%Y%m%d')
        next_batch_number = f'{product.id}-{current_date}'
        
        form = ProductBatchForm(initial={
            'batch_number': next_batch_number,
            'quantity': 0
        })
    
    context = {
        'form': form,
        'product': product,
        'title': f'Create batch for {product.name}',
        'submit_text': 'Save Batch'
    }
    
    return render(request, 'inventory/product/batch_form.html', context)


@login_required
def product_batch_update(request, pk):
    """Update product batch view"""
    batch = get_object_or_404(ProductBatch, pk=pk)
    product = batch.product
    
    if request.method == 'POST':
        form = ProductBatchForm(request.POST, instance=batch)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Batch {batch.batch_number} updated successfully')
            return redirect('product_detail', pk=product.id)
    else:
        form = ProductBatchForm(instance=batch)
    
    context = {
        'form': form,
        'batch': batch,
        'product': product,
        'title': f'Edit Batch: {batch.batch_number}',
        'submit_text': 'Update Batch'
    }
    
    return render(request, 'inventory/product/batch_form.html', context)


@login_required
def product_bulk_create(request):
    """Bulk create products view"""
    if request.method == 'POST':
        form = ProductBulkForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            name_prefix = form.cleaned_data['name_prefix']
            name_suffix_start = form.cleaned_data.get('name_suffix_start', 1)
            name_suffix_end = form.cleaned_data.get('name_suffix_end', 10)
            retail_price = form.cleaned_data['retail_price']
            wholesale_price = form.cleaned_data.get('wholesale_price')
            cost_price = form.cleaned_data.get('cost_price')
            
            created_count = 0
            
            # Create products in bulk
            for i in range(name_suffix_start, name_suffix_end + 1):
                product_name = f"{name_prefix}{i}"
                
                # Check if product already exists
                if Product.objects.filter(name=product_name).exists():
                    continue
                
                product = Product.objects.create(
                    name=product_name,
                    category=category,
                    retail_price=retail_price,
                    wholesale_price=wholesale_price or retail_price,
                    cost_price=cost_price or retail_price * 0.7,
                    created_by=request.user
                )
                
                # Create inventory record
                Inventory.objects.create(
                    product=product,
                    quantity=0,
                    warning_level=5
                )
                
                created_count += 1
            
            messages.success(request, f'Successfully created {created_count} products')
            return redirect('product_list')
    else:
        form = ProductBulkForm()
    
    context = {
        'form': form,
        'title': 'Bulk create products',
        'submit_text': 'Create Products'
    }
    
    return render(request, 'inventory/product/product_bulk_form.html', context)


@login_required
def product_import(request):
    """Import products view"""
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Validate CSV file
            validation_result = validate_csv(csv_file, 
                                            required_headers=['name', 'retail_price'],
                                            expected_headers=['name', 'category', 'retail_price', 
                                                            'wholesale_price', 'cost_price', 
                                                            'barcode', 'sku', 'specification'])
            
            if not validation_result['valid']:
                messages.error(request, f"CSV validation failed: {validation_result['errors']}")
                return render(request, 'inventory/product/product_import.html', {'form': form})
            
            # Process CSV file
            try:
                result = product_service.import_products_from_csv(csv_file, request.user)
                
                messages.success(request, f"Imported {result['success']} products. Skipped {result['skipped']}, Failed {result['failed']}.")
                
                if result['failed_rows']:
                    error_messages = []
                    for row_num, error in result['failed_rows']:
                        error_messages.append(f"Row {row_num}: {error}")
                    
                    # Limit error messages to reasonable length
                    if len(error_messages) > 5:
                        error_messages = error_messages[:5] + [f"... and {len(error_messages) - 5} more errors."]
                    
                    for error in error_messages:
                        messages.warning(request, error)
                
                return redirect('product_list')
            
            except Exception as e:
                messages.error(request, f"Error during import: {str(e)}")
                return render(request, 'inventory/product/product_import.html', {'form': form})
    else:
        form = ProductImportForm()
    
    # Generate sample CSV data
    sample_data = [
        ['name', 'category', 'retail_price', 'wholesale_price', 'cost_price', 'barcode', 'sku', 'specification'],
        ['Sample Product 1', 'Fruits', '10.00', '8.00', '6.00', '123456789', 'SKU001', '500g'],
        ['Sample Product 2', 'Vegetables', '5.50', '4.50', '3.00', '987654321', 'SKU002', '1kg'],
    ]
    
    # Create CSV in memory
    sample_csv = io.StringIO()
    writer = csv.writer(sample_csv)
    for row in sample_data:
        writer.writerow(row)
    
    sample_csv_content = sample_csv.getvalue()
    
    context = {
        'form': form,
        'sample_csv': sample_csv_content,
    }
    
    return render(request, 'inventory/product/product_import.html', context)


@login_required
def product_export(request):
    """Export products view"""
    # Get filter parameters
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    # Base queryset
    products = Product.objects.select_related('category').all()
    
    # Apply filters
    if category_id:
        products = products.filter(category_id=category_id)
    
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    
    # Write CSV
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Category', 'Retail Price', 'Wholesale Price', 'Cost Price', 'Barcode', 'SKU', 'Specification', 'Status'])
    
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.category.name if product.category else '',
            product.retail_price,
            product.wholesale_price,
            product.cost_price,
            product.barcode or '',
            product.sku or '',
            product.specification or '',
            'Active' if product.is_active else 'Inactive',
        ])
    
    return response

# Add alias function for import backward compatibility
def product_edit(request, pk):
    """
    Alias of product_update for backward compatibility
    """
    return product_update(request, pk) 