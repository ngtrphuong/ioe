from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

# Use refactored model imports
from inventory.models import Category, OperationLog
from inventory.forms import CategoryForm

@login_required
def category_list_view(request):
    """Product category list view"""
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def create_category_view(request):
    """Create product category view"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            
            # Log operation
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Added product category: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(category)
            )
            
            messages.success(request, 'Product category added successfully')
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'inventory/category_form.html', {'form': form})

@login_required
def category_edit(request, category_id):
    """Edit product category view"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            
            # Log operation
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Edited product category: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(category)
            )
            
            messages.success(request, 'Product category updated successfully')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'inventory/category_form.html', {'form': form, 'category': category})

@login_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    # Check if the category has associated products
    if category.product_set.exists():
        messages.error(request, f'Cannot delete category "{category.name}" because products are associated with it')
        return redirect('category_list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        
        # Log operation
        OperationLog.objects.create(
            operator=request.user,
            operation_type='OTHER',
            details=f'Deleted product category: {category_name}',
            related_object_id=0,  # Deleted, no ID
            related_content_type=ContentType.objects.get_for_model(Category)
        )
        
        messages.success(request, f'Category "{category_name}" deleted successfully')
        return redirect('category_list')
    
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})

@login_required
def category_list(request):
    return category_list_view(request)

@login_required
def category_create(request):
    return create_category_view(request)