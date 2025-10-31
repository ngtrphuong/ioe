from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Sum
from .models import Product, Category, Inventory, Sale, SaleItem, InventoryTransaction, Member, MemberLevel, RechargeRecord
from django.http import JsonResponse
from .models import OperationLog
from django.db.models import Q
from decimal import Decimal
from django.utils import timezone
import re


def product_by_barcode(request, barcode):
    try:
        # First try exact barcode match
        product = Product.objects.get(barcode=barcode)
        # Get inventory information
        try:
            inventory = Inventory.objects.get(product=product)
            stock = inventory.quantity
        except Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'name': product.name,
            'price': product.price,
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except Product.DoesNotExist:
        # If no exact match, try fuzzy match with barcode
        products = Product.objects.filter(barcode__icontains=barcode).order_by('barcode')[:5]
        if products.exists():
            # Return multiple matching products
            product_list = []
            for product in products:
                try:
                    inventory = Inventory.objects.get(product=product)
                    stock = inventory.quantity
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

# New member search API
def member_search_by_phone(request, phone):
    """
    API to search members by phone number
    Supports exact match and fuzzy match, returns multiple matching results
    """
    try:
        # First try exact phone number match
        member = Member.objects.get(phone=phone)
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'member_id': member.id,
            'member_name': member.name,
            'member_level': member.level.name,
            'member_balance': float(member.balance),
            'member_points': member.points,
            'member_gender': member.get_gender_display(),
            'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            'member_total_spend': float(member.total_spend),
            'member_purchase_count': member.purchase_count
        })
    except Member.DoesNotExist:
        # If exact match fails, try fuzzy match on phone number or name
        members = Member.objects.filter(
            Q(phone__icontains=phone) | 
            Q(name__icontains=phone)
        ).order_by('phone')[:5]  # Limit number of results
        
        if members.exists():
            # If only one match result
            if members.count() == 1:
                member = members.first()
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'member_id': member.id,
                    'member_name': member.name,
                    'member_level': member.level.name,
                    'member_balance': float(member.balance),
                    'member_points': member.points,
                    'member_gender': member.get_gender_display(),
                    'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
                    'member_total_spend': float(member.total_spend),
                    'member_purchase_count': member.purchase_count
                })
            # If multiple match results
            else:
                member_list = []
                for member in members:
                    member_list.append({
                        'member_id': member.id,
                        'member_name': member.name,
                        'member_phone': member.phone,
                        'member_level': member.level.name,
                        'member_balance': float(member.balance),
                        'member_points': member.points
                    })
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'members': member_list
                })
        else:
            return JsonResponse({'success': False, 'message': 'Member not found'})
            
from .forms import ProductForm, InventoryTransactionForm, SaleForm, SaleItemForm, MemberForm

@login_required
def index(request):
    products = Product.objects.all()[:5]  # Get latest 5 products
    low_stock_items = Inventory.objects.filter(quantity__lte=F('warning_level'))[:5]  # Get low stock alert items
    context = {
        'products': products,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'inventory/index.html', context)

@login_required
def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'inventory/product_list.html', {'products': products, 'categories': categories})

@login_required
def inventory_list(request):
    # Get filter parameters
    category_id = request.GET.get('category', '')
    color = request.GET.get('color', '')
    size = request.GET.get('size', '')
    search_query = request.GET.get('search', '')
    
    # Base query
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
def sale_list(request):
    sales = Sale.objects.all().order_by('-created_at')
    return render(request, 'inventory/sale_list.html', {'sales': sales})

@login_required
def sale_detail(request, sale_id):
    """Sale order detail view"""
    sale = get_object_or_404(Sale, pk=sale_id)
    items = sale.items.all()
    
    context = {
        'sale': sale,
        'items': items,
    }
    
    return render(request, 'inventory/sale_detail.html', context)

@login_required
def product_create(request):
    initial_data = {}
    
    # If redirected from barcode API, pre-fill form
    if request.method == 'GET' and 'barcode' in request.GET:
        initial_data = {
            'barcode': request.GET.get('barcode', ''),
            'name': request.GET.get('name', ''),
            'price': request.GET.get('price', 0),
            'specification': request.GET.get('specification', ''),
            'manufacturer': request.GET.get('manufacturer', ''),
            'description': request.GET.get('description', '')
        }
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            Inventory.objects.create(product=product)
            
            # Log operation
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Add new product: {product.name} (Barcode: {product.barcode})',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(Product)
            )
            
            messages.success(request, 'Product added successfully')
            return redirect('product_list')
    else:
        form = ProductForm(initial=initial_data)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'is_from_barcode_api': bool(initial_data)
    })

@login_required
def product_edit(request, product_id):
    """Edit product information"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            
            # Log operation
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'Edit product: {product.name} (Barcode: {product.barcode})',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(Product)
            )
            
            messages.success(request, 'Product info updated successfully')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'is_edit': True
    })

@login_required
def inventory_transaction_create(request):
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
            
            messages.success(request, 'Stock-in operation succeeded')
            return redirect('inventory_list')
    else:
        form = InventoryTransactionForm()
    return render(request, 'inventory/inventory_form.html', {'form': form})

@login_required
def sale_create(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.operator = request.user
            
            # Add member association
            member_id = request.POST.get('member')
            if member_id:
                try:
                    member = Member.objects.get(id=member_id)
                    sale.member = member
                except Member.DoesNotExist:
                    pass
                
            sale.save()
            messages.success(request, 'Sale order created successfully')
            return redirect('sale_item_create', sale_id=sale.id)
    else:
        form = SaleForm()
    
    # Get member level list for add member modal
    member_levels = MemberLevel.objects.all()
    
    return render(request, 'inventory/sale_form.html', {
        'form': form,
        'member_levels': member_levels
    })

@login_required
def sale_item_create(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    if request.method == 'POST':
        form = SaleItemForm(request.POST)
        if form.is_valid():
            sale_item = form.save(commit=False)
            sale_item.sale = sale
            
            inventory = Inventory.objects.get(product=sale_item.product)
            if inventory.quantity >= sale_item.quantity:
                inventory.quantity -= sale_item.quantity
                inventory.save()
                
                sale_item.save()
                sale.update_total_amount()
                
                transaction = InventoryTransaction.objects.create(
                    product=sale_item.product,
                    transaction_type='OUT',
                    quantity=sale_item.quantity,
                    operator=request.user,
                    notes=f'Sale order number: {sale.id}'
                )
                
                messages.success(request, 'Product added successfully')
                
                # Log operation
                from django.contrib.contenttypes.models import ContentType
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='SALE',
                    details=f'Sell product {sale_item.product.name} quantity {sale_item.quantity}',
                    related_object_id=sale.id,
                    related_content_type=ContentType.objects.get_for_model(Sale)
                )
                return redirect('sale_item_create', sale_id=sale.id)
            else:
                messages.error(request, 'Insufficient stock')
    else:
        form = SaleItemForm()
    
    sale_items = sale.items.all()
    return render(request, 'inventory/sale_item_form.html', {
        'form': form,
        'sale': sale,
        'sale_items': sale_items
    })

@login_required
def member_list(request):
    sort_by = request.GET.get('sort', 'name')
    
    # Query members based on sort parameter
    if sort_by == 'total_spend':
        members = Member.objects.all().order_by('-total_spend')
        sort_label = 'Total Spend'
    elif sort_by == 'purchase_count':
        members = Member.objects.all().order_by('-purchase_count')
        sort_label = 'Purchase Count'
    else:
        members = Member.objects.all().order_by('name')
        sort_by = 'name'  # Prevent injection
        sort_label = 'Name'
    
    member_levels = MemberLevel.objects.all()
    
    return render(request, 'inventory/member_list.html', {
        'members': members, 
        'member_levels': member_levels,
        'sort_by': sort_by,
        'sort_label': sort_label
    })

@login_required
def member_create(request):
    # Allow administrators to create multiple members
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            # Allow creating independent member records
            member.save()
            messages.success(request, 'Member added successfully')
            return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'inventory/member_form.html', {'form': form})

@login_required
def member_edit(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member info updated successfully')
            return redirect('member_list')
    else:
        form = MemberForm(instance=member)
    return render(request, 'inventory/member_form.html', {'form': form})

@login_required
def member_purchases(request):
    """Member consumption record query view"""
    search_term = request.GET.get('search', '')
    
    if search_term:
        # Query member by name or phone number
        member = None
        sales = []
        
        try:
            # First try to find by phone number
            member = Member.objects.get(phone=search_term)
            sales = Sale.objects.filter(member=member).order_by('-created_at')
        except Member.DoesNotExist:
            # Then try fuzzy search by name
            members = Member.objects.filter(name__icontains=search_term)
            if members.exists():
                # Use first one if multiple members found
                member = members.first()
                sales = Sale.objects.filter(member=member).order_by('-created_at')
                
        return render(request, 'inventory/member_purchases.html', {
            'search_term': search_term,
            'member': member,
            'sales': sales
        })
    
    return render(request, 'inventory/member_purchases.html', {
        'search_term': '',
        'member': None,
        'sales': []
    })

@login_required
def member_level_list(request):
    """Member level list view"""
    levels = MemberLevel.objects.all().order_by('points_threshold')
    return render(request, 'inventory/member_level_list.html', {'levels': levels})

@login_required
def member_level_create(request):
    """Create member level view"""
    from .forms import MemberLevelForm
    
    if request.method == 'POST':
        form = MemberLevelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member level added successfully')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm()
        
    return render(request, 'inventory/member_level_form.html', {'form': form})

@login_required
def member_level_edit(request, level_id):
    """Edit member level view"""
    from .forms import MemberLevelForm
    
    level = get_object_or_404(MemberLevel, id=level_id)
    if request.method == 'POST':
        form = MemberLevelForm(request.POST, instance=level)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member level updated successfully')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm(instance=level)
        
    return render(request, 'inventory/member_level_form.html', {'form': form, 'level': level})

@login_required
def member_recharge(request, member_id):
    """Member recharge view"""
    member = get_object_or_404(Member, id=member_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        actual_amount = Decimal(request.POST.get('actual_amount', '0'))
        payment_method = request.POST.get('payment_method', 'cash')
        remark = request.POST.get('remark', '')
        
        if amount <= 0:
            messages.error(request, 'Recharge amount must be greater than 0')
            return redirect('member_recharge', member_id=member_id)
        
        # Create recharge record
        recharge = RechargeRecord.objects.create(
            member=member,
            amount=amount,
            actual_amount=actual_amount,
            payment_method=payment_method,
            operator=request.user,
            remark=remark
        )
        
        # Update member balance and status
        member.balance += amount
        member.is_recharged = True
        member.save()
        
        # Log operation
        from django.contrib.contenttypes.models import ContentType
        OperationLog.objects.create(
            operator=request.user,
            operation_type='MEMBER',
            details=f'Recharge {amount} for member {member.name}',
            related_object_id=recharge.id,
            related_content_type=ContentType.objects.get_for_model(RechargeRecord)
        )
        
        messages.success(request, f'Successfully recharged {amount} for {member.name}')
        return redirect('member_list')
    
    return render(request, 'inventory/member_recharge.html', {
        'member': member
    })

@login_required
def member_recharge_records(request, member_id):
    """Member recharge record view"""
    member = get_object_or_404(Member, id=member_id)
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')
    
    return render(request, 'inventory/member_recharge_records.html', {
        'member': member,
        'recharge_records': recharge_records
    })

@login_required
def birthday_members_report(request):
    """Current month birthday members report"""
    # Get current month
    current_month = timezone.now().month
    current_month_name = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
        7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }[current_month]
    
    # Get members with birthdays this month
    members = Member.objects.filter(birthday__month=current_month).order_by('id')
    
    # Count member level distribution
    level_counts = {}
    levels_data = []
    
    for member in members:
        if member.level:
            level_id = member.level.id
            if level_id not in level_counts:
                level_counts[level_id] = {
                    'id': level_id,
                    'name': member.level.name,
                    'color': member.level.color,
                    'color_code': f'#{member.level.color}' if member.level.color.startswith('gradient-') else member.level.color,
                    'count': 0
                }
            level_counts[level_id]['count'] += 1
    
    levels_data = list(level_counts.values())
    
    # Count birthday date distribution (days 1-31)
    days_distribution = [0] * 31
    for member in members:
        if member.birthday:
            day = member.birthday.day
            if 1 <= day <= 31:
                days_distribution[day - 1] += 1
    
    context = {
        'current_month_name': current_month_name,
        'members': members,
        'levels': levels_data,
        'days_distribution': days_distribution
    }
    
    return render(request, 'inventory/birthday_members_report.html', context)

@login_required
def member_details(request, member_id):
    """Member detail information view, including consumption records and recharge records"""
    member = get_object_or_404(Member, id=member_id)
    
    # Get member's consumption records
    sales = Sale.objects.filter(member=member).order_by('-created_at')
    
    # Get member's recharge records
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')
    
    return render(request, 'inventory/member_details.html', {
        'member': member,
        'sales': sales,
        'recharge_records': recharge_records
    })

# Reports center related views
@login_required
def reports_index(request):
    """Reports center home page, showing all available reports and their statistics"""
    # Get current month birthday member count
    current_month = timezone.now().month
    birthday_members_count = Member.objects.filter(birthday__month=current_month).count()
    
    # Get sales record count
    total_sales_count = Sale.objects.count()
    
    # Get low stock product count
    low_stock_count = Inventory.objects.filter(quantity__lt=F('warning_level')).count() or 0
    
    # Get total recharge amount
    total_recharge_amount = RechargeRecord.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get current month sales amount
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales_amount = Sale.objects.filter(
        created_at__gte=current_month_start
    ).aggregate(total=Sum('final_amount'))['total'] or 0
    
    # Get today's operation log count
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_log_count = OperationLog.objects.filter(timestamp__gte=today_start).count()
    
    context = {
        'birthday_members_count': birthday_members_count,
        'total_sales_count': total_sales_count,
        'low_stock_count': low_stock_count,
        'total_recharge_amount': total_recharge_amount,
        'monthly_sales_amount': monthly_sales_amount,
        'today_log_count': today_log_count,
    }
    
    return render(request, 'inventory/reports_index.html', context)

@login_required
def member_add_ajax(request):
    """AJAX add member"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            level_id = request.POST.get('level')
            
            # Detailed data validation
            errors = {}
            if not name:
                errors['name'] = 'Member name cannot be empty'
            if not phone:
                errors['phone'] = 'Phone number cannot be empty'
            elif not re.match(r'^\d{11}$', phone):
                errors['phone'] = 'Please enter an 11-digit mobile number'
            if not level_id:
                errors['level'] = 'Please select a member level'
            
            if errors:
                return JsonResponse({
                    'success': False, 
                    'message': 'Form validation failed',
                    'errors': errors
                })
            
            # Check if phone number already exists
            if Member.objects.filter(phone=phone).exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'This phone number is already registered as a member, please use another phone number'
                })
            
            # Get member level
            try:
                level = MemberLevel.objects.get(id=level_id)
            except MemberLevel.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'message': 'Selected member level does not exist, please select again'
                })
            
            # Create member
            member = Member.objects.create(
                name=name,
                phone=phone,
                level=level,
                points=0,
                balance=0
            )
            
            # Log operation
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='MEMBER',
                details=f'Add member: {name} (Phone: {phone})',
                related_object_id=member.id,
                related_content_type=ContentType.objects.get_for_model(Member)
            )
            
            return JsonResponse({
                'success': True,
                'member_id': member.id,
                'member_name': member.name,
                'member_phone': member.phone,
                'member_level': member.level.name
            })
            
        except Exception as e:
            import traceback
            print(f"Member add error: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False, 
                'message': f'Error adding member: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Unsupported request method'})