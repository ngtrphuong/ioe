"""
Inventory management views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from inventory.models import (
    Product, Inventory, InventoryTransaction, 
    OperationLog, StockAlert, check_inventory,
    update_inventory, Category
)
from inventory.forms import InventoryTransactionForm


@login_required
def inventory_list(request):
    """Inventory list view"""
    # Get filter parameters
    category_id = request.GET.get('category', '')
    color = request.GET.get('color', '')
    size = request.GET.get('size', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    inventory_items = Inventory.objects.select_related('product', 'product__category').all()
    
    # Apply filter conditions
    if category_id:
        inventory_items = inventory_items.filter(product__category_id=category_id)
    
    if color:
        inventory_items = inventory_items.filter(product__color=color)
    
    if size:
        inventory_items = inventory_items.filter(product__size=size)
    
    if search_query:
        inventory_items = inventory_items.filter(
            Q(product__name__icontains=search_query) | 
            Q(product__barcode__icontains=search_query)
        )
    
    # Get all categories
    categories = Category.objects.all()
    
    # Get all available colors and sizes
    colors = Product.COLOR_CHOICES
    sizes = Product.SIZE_CHOICES
    
    context = {
        'inventory_items': inventory_items,
        'categories': categories,
        'colors': colors,
        'sizes': sizes,
        'selected_category': category_id,
        'selected_color': color,
        'selected_size': size,
        'search_query': search_query,
    }
    
    return render(request, 'inventory/inventory_list.html', context)


@login_required
def inventory_transaction_list(request):
    """Inventory transaction list - shows all inbound, outbound, and adjustment records"""
    # Get filter parameters
    transaction_type = request.GET.get('type', '')
    product_id = request.GET.get('product_id', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    transactions = InventoryTransaction.objects.select_related('product', 'operator').all()
    
    # Apply filter conditions
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    
    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query) | 
            Q(product__barcode__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    if date_from:
        from datetime import datetime
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            transactions = transactions.filter(created_at__gte=date_from)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        from datetime import datetime, timedelta
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # Add one day to include the entire day
            transactions = transactions.filter(created_at__lt=date_to)
        except (ValueError, TypeError):
            pass
    
    # Sort
    transactions = transactions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)  # 20 records per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/inventory_transaction_list.html', {
        'page_obj': page_obj,
        'transaction_type': transaction_type,
        'product_id': product_id,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': dict(InventoryTransaction.TRANSACTION_TYPES)
    })


@login_required
def inventory_in(request):
    """Stock-in view"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # Update inventory using helper function
            success, inventory, result = update_inventory(
                product=product,
                quantity=quantity,  # Positive means stock-in
                transaction_type='IN',
                operator=request.user,
                notes=notes
            )
            
            if success:
                # Record operation log
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'Stock-in: {product.name} x {quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} stocked in successfully, current inventory: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'Stock-in failed: {result}')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_transaction_form.html', {
        'form': form,
        'form_title': 'Stock-in',
        'submit_text': 'Confirm Stock-in',
        'transaction_type': 'IN'
    })


@login_required
def inventory_out(request):
    """Stock-out view"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # Check if inventory is sufficient first
            if not check_inventory(product, quantity):
                messages.error(request, f'Stock-out failed: insufficient stock for {product.name}')
                return render(request, 'inventory/inventory_transaction_form.html', {
                    'form': form,
                    'form_title': 'Stock-out',
                    'submit_text': 'Confirm Stock-out',
                    'transaction_type': 'OUT'
                })
            
            # Update inventory using helper function
            success, inventory, result = update_inventory(
                product=product,
                quantity=-quantity,  # Negative means stock-out
                transaction_type='OUT',
                operator=request.user,
                notes=notes
            )
            
            if success:
                # Record operation log
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'Stock-out: {product.name} x {quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} stocked out successfully, current inventory: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'Stock-out failed: {result}')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_transaction_form.html', {
        'form': form,
        'form_title': 'Stock-out',
        'submit_text': 'Confirm Stock-out',
        'transaction_type': 'OUT'
    })


@login_required
def inventory_adjust(request):
    """Inventory adjustment view"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # Get current inventory
            try:
                inventory = Inventory.objects.get(product=product)
                current_quantity = inventory.quantity
            except Inventory.DoesNotExist:
                current_quantity = 0
            
            # Calculate adjustment value
            adjustment_action = request.POST.get('adjustment_action')
            if adjustment_action == 'set':
                # Set to specified quantity
                if quantity < 0:
                    messages.error(request, 'Inventory quantity cannot be negative')
                    return render(request, 'inventory/inventory_adjust_form.html', {
                        'form': form,
                        'current_quantity': current_quantity
                    })
                
                adjustment_value = quantity - current_quantity
            elif adjustment_action == 'add':
                # Increase by specified quantity
                adjustment_value = quantity
            elif adjustment_action == 'subtract':
                # Decrease by specified quantity
                if quantity > current_quantity:
                    messages.error(request, f'Reduction amount ({quantity}) exceeds current inventory ({current_quantity})')
                    return render(request, 'inventory/inventory_adjust_form.html', {
                        'form': form,
                        'current_quantity': current_quantity
                    })
                
                adjustment_value = -quantity
            else:
                messages.error(request, 'Please select a valid adjustment method')
                return render(request, 'inventory/inventory_adjust_form.html', {
                    'form': form,
                    'current_quantity': current_quantity
                })
            
            # Update inventory using helper function
            success, inventory, result = update_inventory(
                product=product,
                quantity=adjustment_value,
                transaction_type='ADJUST',
                operator=request.user,
                notes=f"{notes} (before adjustment: {current_quantity})"
            )
            
            if success:
                # Record operation log
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'Inventory adjustment: {product.name} from {current_quantity} to {inventory.quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} inventory adjusted successfully, current inventory: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'Inventory adjustment failed: {result}')
    else:
        form = InventoryTransactionForm()
        product_id = request.GET.get('product_id')
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                form.fields['product'].initial = product
            except Product.DoesNotExist:
                pass
    
    # Get current inventory (if product selected)
    current_quantity = 0
    if form.initial.get('product'):
        try:
            inventory = Inventory.objects.get(product=form.initial['product'])
            current_quantity = inventory.quantity
        except Inventory.DoesNotExist:
            pass
    
    return render(request, 'inventory/inventory_adjust_form.html', {
        'form': form,
        'current_quantity': current_quantity
    })


@login_required
def inventory_transaction_create(request):
    """Create stock-in transaction view"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.transaction_type = 'IN'
            transaction.operator = request.user
            transaction.save()
            
            inventory = Inventory.objects.get(product=transaction.product)
            inventory.quantity += transaction.quantity
            inventory.save()
            
            # Record operation log
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Stock-in operation: {transaction.product.name}, quantity: {transaction.quantity}',
                related_object_id=transaction.id,
                related_content_type=ContentType.objects.get_for_model(InventoryTransaction)
            )
            
            messages.success(request, 'Stock-in operation successful')
            return redirect('inventory_list')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_form.html', {'form': form}) 