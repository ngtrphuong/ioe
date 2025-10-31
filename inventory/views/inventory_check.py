"""
Inventory checking views.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

# Use refactored model imports
from inventory.models import (
    InventoryCheck, InventoryCheckItem, Product, 
    Inventory, OperationLog
)
from inventory.forms import InventoryCheckForm, InventoryCheckItemForm, InventoryCheckApproveForm
from inventory.services.inventory_check_service import InventoryCheckService
from inventory.utils.logging import log_view_access
from inventory.permissions.decorators import permission_required

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_list(request):
    """Inventory check list view"""
    inventory_checks = InventoryCheck.objects.all().order_by('-created_at')
    
    # Search and filter
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        inventory_checks = inventory_checks.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if status_filter:
        inventory_checks = inventory_checks.filter(status=status_filter)
    
    return render(request, 'inventory/inventory_check_list.html', {
        'inventory_checks': inventory_checks,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': InventoryCheck.STATUS_CHOICES,
    })

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_create(request):
    """View to create a new inventory check."""
    if request.method == 'POST':
        form = InventoryCheckForm(request.POST)
        if form.is_valid():
            # Extract category if specified
            category = form.cleaned_data.get('category')
            
            # Use the service to create the inventory check
            try:
                inventory_check = InventoryCheckService.create_inventory_check(
                    name=form.cleaned_data['name'],
                    description=form.cleaned_data['description'],
                    user=request.user,
                    category=category
                )
                
                messages.success(request, f'Inventory check {inventory_check.name} created successfully')
                return redirect('inventory_check_detail', check_id=inventory_check.id)
            except Exception as e:
                messages.error(request, f'Error creating inventory check: {str(e)}')
    else:
        form = InventoryCheckForm()
    
    return render(request, 'inventory/inventory_check_form.html', {
        'form': form,
        'form_title': 'Create Inventory Check',
        'submit_text': 'Create',
    })

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_detail(request, check_id):
    """View to show inventory check details."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    
    # Get inventory check items with products
    check_items = inventory_check.items.all().select_related('product')
    
    # Get summary information
    summary = InventoryCheckService.get_inventory_check_summary(inventory_check)
    
    return render(request, 'inventory/inventory_check_detail.html', {
        'inventory_check': inventory_check,
        'check_items': check_items,
        'summary': summary,
    })

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_item_update(request, check_id, item_id):
    """View to record actual quantity for an inventory check item."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    check_item = get_object_or_404(InventoryCheckItem, id=item_id, inventory_check=inventory_check)
    
    if request.method == 'POST':
        form = InventoryCheckItemForm(request.POST, instance=check_item)
        if form.is_valid():
            try:
                # Use the service to record the check
                InventoryCheckService.record_check_item(
                    inventory_check_item=check_item,
                    actual_quantity=form.cleaned_data['actual_quantity'],
                    user=request.user,
                    notes=form.cleaned_data['notes']
                )
                
                messages.success(request, f'Check record updated for {check_item.product.name}')
                return redirect('inventory_check_detail', check_id=check_id)
            except Exception as e:
                messages.error(request, f'Error updating check record: {str(e)}')
    else:
        form = InventoryCheckItemForm(instance=check_item)
    
    return render(request, 'inventory/inventory_check_item_form.html', {
        'form': form,
        'inventory_check': inventory_check,
        'check_item': check_item,
        'form_title': f'Check Product: {check_item.product.name}',
        'submit_text': 'Save',
    })

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_start(request, check_id):
    """View to start an inventory check."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    
    try:
        InventoryCheckService.start_inventory_check(
            inventory_check=inventory_check,
            user=request.user
        )
        
        messages.success(request, f'Inventory check {inventory_check.name} started')
    except Exception as e:
        messages.error(request, f'Error starting inventory check: {str(e)}')
    
    return redirect('inventory_check_detail', check_id=check_id)

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_complete(request, check_id):
    """View to complete an inventory check."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    
    try:
        InventoryCheckService.complete_inventory_check(
            inventory_check=inventory_check,
            user=request.user
        )
        
        messages.success(request, f'Inventory check {inventory_check.name} completed')
    except Exception as e:
        messages.error(request, f'Error completing inventory check: {str(e)}')
    
    return redirect('inventory_check_detail', check_id=check_id)

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('approve_inventory_check')
def inventory_check_approve(request, check_id):
    """View to approve an inventory check."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    
    if request.method == 'POST':
        form = InventoryCheckApproveForm(request.POST)
        if form.is_valid():
            try:
                adjust_inventory = form.cleaned_data['adjust_inventory']
                
                InventoryCheckService.approve_inventory_check(
                    inventory_check=inventory_check,
                    user=request.user,
                    adjust_inventory=adjust_inventory
                )
                
                messages.success(
                    request,
                    f'Inventory check {inventory_check.name} approved' + 
                    (" and inventory adjusted" if adjust_inventory else "")
                )
                return redirect('inventory_check_detail', check_id=check_id)
            except Exception as e:
                messages.error(request, f'Error approving inventory check: {str(e)}')
    else:
        form = InventoryCheckApproveForm()
    
    # Get discrepancy summary
    items_with_discrepancy = inventory_check.items.filter(difference__isnull=False).exclude(difference=0)
    
    return render(request, 'inventory/inventory_check_approve.html', {
        'form': form,
        'inventory_check': inventory_check,
        'items_with_discrepancy': items_with_discrepancy,
        'form_title': f'Approve Inventory Check: {inventory_check.name}',
        'submit_text': 'Approve',
    })

@login_required
@log_view_access('INVENTORY_CHECK')
@permission_required('perform_inventory_check')
def inventory_check_cancel(request, check_id):
    """View to cancel an inventory check."""
    inventory_check = get_object_or_404(InventoryCheck, id=check_id)
    
    try:
        InventoryCheckService.cancel_inventory_check(
            inventory_check=inventory_check,
            user=request.user
        )
        
        messages.success(request, f'Inventory check {inventory_check.name} cancelled')
    except Exception as e:
        messages.error(request, f'Error cancelling inventory check: {str(e)}')
    
    return redirect('inventory_check_detail', check_id=check_id) 