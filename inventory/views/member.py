import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from decimal import Decimal

# Import from the new model structure
from ..models import Member, MemberLevel, RechargeRecord, OperationLog, Sale, MemberTransaction
from ..forms import MemberForm, MemberLevelForm, RechargeForm, MemberImportForm
from ..utils import validate_csv
from ..services import member_service

import csv
import io
import uuid
from datetime import datetime, timedelta


def member_search_by_phone(request, phone):
    """
    API to search members by phone number.
    Supports exact and fuzzy matching, returns multiple matches when applicable.
    """
    try:
        # Try exact phone match first
        member = Member.objects.get(phone=phone)
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'member_id': member.id,
            'member_name': member.name,
            'member_phone': member.phone,
            'member_level': member.level.name,
            'discount_rate': float(member.level.discount),
            'member_balance': float(member.balance),
            'member_points': member.points,
            'member_gender': member.get_gender_display(),
            'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            'member_total_spend': float(member.total_spend),
            'member_purchase_count': member.purchase_count
        })
    except Member.DoesNotExist:
        # If exact match fails, try fuzzy match on phone or name
        members = Member.objects.filter(
            models.Q(phone__icontains=phone) |
            models.Q(name__icontains=phone)
        ).order_by('phone')[:5]  # Limit number of results

        if members.exists():
            # If only one match
            if members.count() == 1:
                member = members.first()
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'member_id': member.id,
                    'member_name': member.name,
                    'member_phone': member.phone,
                    'member_level': member.level.name,
                    'discount_rate': float(member.level.discount),
                    'member_balance': float(member.balance),
                    'member_points': member.points,
                    'member_gender': member.get_gender_display(),
                    'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
                    'member_total_spend': float(member.total_spend),
                    'member_purchase_count': member.purchase_count
                })
            # If multiple matches
            else:
                member_list = []
                for member in members:
                    member_list.append({
                        'member_id': member.id,
                        'member_name': member.name,
                        'member_phone': member.phone,
                        'member_level': member.level.name,
                        'discount_rate': float(member.level.discount),
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


@login_required
def member_list(request):
    """Member list view"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    filter_level = request.GET.get('level', '')
    is_active_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')

    # Base queryset
    members = Member.objects.select_related('level').all()

    # Apply filtering
    if search_query:
        members = members.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    if filter_level:
        members = members.filter(level_id=filter_level)

    if is_active_filter == 'active':
        members = members.filter(is_active=True)
    elif is_active_filter == 'inactive':
        members = members.filter(is_active=False)

    # Sorting
    if sort_by == 'name':
        members = members.order_by('name')
    elif sort_by == 'created_desc':
        members = members.order_by('-created_at')

    # Pagination
    paginator = Paginator(members, 15)  # 15 members per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get member levels list for filtering
    levels = MemberLevel.objects.filter(is_active=True).order_by('priority')

    # Calculate statistics
    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()

    context = {
        'page_obj': page_obj,
        'levels': levels,
        'search_query': search_query,
        'selected_level': filter_level,
        'selected_status': is_active_filter,
        'sort_by': sort_by,
        'total_members': total_members,
        'active_members': active_members,
    }

    return render(request, 'inventory/member/member_list.html', context)


@login_required
def member_detail(request, pk):
    """Member detail view"""
    member = get_object_or_404(Member, pk=pk)

    # Get member transaction records
    transactions = MemberTransaction.objects.filter(member=member).order_by('-created_at')[:20]

    # Get member purchase records
    sales = Sale.objects.filter(member=member).order_by('-created_at')[:20]

    # Calculate statistics
    total_spent = Sale.objects.filter(member=member).aggregate(total=Sum('total_amount'))['total'] or 0
    visit_count = Sale.objects.filter(member=member).count()

    # Last 30-day statistics
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_spent = Sale.objects.filter(member=member, created_at__gte=thirty_days_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    recent_visit_count = Sale.objects.filter(member=member, created_at__gte=thirty_days_ago).count()

    context = {
        'member': member,
        'transactions': transactions,
        'sales': sales,
        'total_spent': total_spent,
        'visit_count': visit_count,
        'recent_spent': recent_spent,
        'recent_visit_count': recent_visit_count,
    }

    return render(request, 'inventory/member/member_detail.html', context)


@login_required
def member_create(request):
    """Create member view"""
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            # Save member data
            member = form.save(commit=False)

            # Generate a member ID if not provided
            if not member.member_id:
                current_date = datetime.now().strftime('%Y%m%d')
                random_suffix = str(uuid.uuid4().int)[:6]  # Use first 6 digits of UUID
                member.member_id = f'M{current_date}{random_suffix}'

            member.created_by = request.user
            member.save()

            messages.success(request, f'Member {member.name} created successfully')

            # If need to continue adding
            if 'save_and_add' in request.POST:
                return redirect('member_create')

            return redirect('member_detail', pk=member.id)
    else:
        form = MemberForm()

        # Generate default member ID
        current_date = datetime.now().strftime('%Y%m%d')
        random_suffix = str(uuid.uuid4().int)[:6]  # Use first 6 digits of UUID
        default_member_id = f'M{current_date}{random_suffix}'

        form.fields['member_id'].initial = default_member_id

        # Set default member level
        try:
            default_level = MemberLevel.objects.filter(is_active=True, is_default=True).first()
            if default_level:
                form.fields['level'].initial = default_level.id
        except:
            pass

    context = {
        'form': form,
        'title': 'Create Member',
        'submit_text': 'Save Member',
    }

    return render(request, 'inventory/member/member_form.html', context)


@login_required
def member_update(request, pk):
    """Update member view"""
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            # Save member data
            member = form.save(commit=False)
            member.updated_at = timezone.now()
            member.updated_by = request.user
            member.save()

            messages.success(request, f'Member {member.name} updated successfully')
            return redirect('member_detail', pk=member.id)
    else:
        form = MemberForm(instance=member)

    context = {
        'form': form,
        'member': member,
        'title': f'Edit Member: {member.name}',
        'submit_text': 'Update Member',
    }

    return render(request, 'inventory/member/member_form.html', context)


@login_required
def member_delete(request, pk):
    """Delete member view"""
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        member_name = member.name

        # Mark as inactive instead of actual deletion
        member.is_active = False
        member.updated_at = timezone.now()
        member.updated_by = request.user
        member.save()

        messages.success(request, f'Member {member_name} marked as inactive')
        return redirect('member_list')

    return render(request, 'inventory/member/member_confirm_delete.html', {
        'member': member
    })


@login_required
def member_level_list(request):
    """Member level list view"""
    # Get member levels
    levels = MemberLevel.objects.all().order_by('priority')

    # Add member count statistics
    levels = levels.annotate(member_count=Count('member'))

    context = {
        'levels': levels,
    }

    return render(request, 'inventory/member/level_list.html', context)


@login_required
def member_level_create(request):
    """Create member level view"""
    if request.method == 'POST':
        form = MemberLevelForm(request.POST)
        if form.is_valid():
            level = form.save()
            messages.success(request, f'Member level {level.name} created successfully')
            return redirect('member_level_list')
    else:
        # Get maximum priority
        max_priority = MemberLevel.objects.aggregate(max_priority=Count('priority'))['max_priority'] or 0

        form = MemberLevelForm(initial={'priority': max_priority + 1})

    context = {
        'form': form,
        'title': 'Create Member Level',
        'submit_text': 'Save Level',
    }

    return render(request, 'inventory/member/level_form.html', context)


@login_required
def member_level_update(request, pk):
    """Update member level view"""
    level = get_object_or_404(MemberLevel, pk=pk)

    if request.method == 'POST':
        form = MemberLevelForm(request.POST, instance=level)
        if form.is_valid():
            level = form.save()
            messages.success(request, f'Member level {level.name} updated successfully')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm(instance=level)

    context = {
        'form': form,
        'level': level,
        'title': f'Edit Member Level: {level.name}',
        'submit_text': 'Update Level',
    }

    return render(request, 'inventory/member/level_form.html', context)


@login_required
def member_level_delete(request, pk):
    """Delete member level view"""
    level = get_object_or_404(MemberLevel, pk=pk)

    # Check if any member is using this level
    member_count = Member.objects.filter(level=level).count()

    # Check if this is the default level
    is_default = level.is_default

    if request.method == 'POST':
        if member_count > 0 and not request.POST.get('force_delete'):
            messages.error(request, f'Cannot delete level {level.name} with {member_count} members')
            return redirect('member_level_list')

        if is_default and not request.POST.get('force_delete'):
            messages.error(request, f'Cannot delete default level {level.name}')
            return redirect('member_level_list')

        level_name = level.name

        # If force delete, move members to default level
        if member_count > 0:
            default_level = None
            if not level.is_default:
                default_level = MemberLevel.objects.filter(is_default=True).first()

            if not default_level:
                default_level = MemberLevel.objects.exclude(id=level.id).first()

            if default_level:
                Member.objects.filter(level=level).update(level=default_level)

        # Delete level
        level.delete()

        messages.success(request, f'Member level {level_name} deleted')
        return redirect('member_level_list')

    context = {
        'level': level,
        'member_count': member_count,
        'is_default': is_default,
    }

    return render(request, 'inventory/member/level_confirm_delete.html', context)


@login_required
def member_import(request):
    """Import members view"""
    if request.method == 'POST':
        form = MemberImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            # Validate CSV file
            validation_result = validate_csv(csv_file,
                                            required_headers=['name', 'phone'],
                                            expected_headers=['name', 'phone', 'email',
                                                            'member_id', 'level', 'points',
                                                            'birthday', 'address'])

            if not validation_result['valid']:
                messages.error(request, f"CSV validation failed: {validation_result['errors']}")
                return render(request, 'inventory/member/member_import.html', {'form': form})

            # Process CSV file
            try:
                result = member_service.import_members_from_csv(csv_file, request.user)

                messages.success(request, f"Imported {result['success']} members. Skipped {result['skipped']}, Failed {result['failed']}.")

                if result['failed_rows']:
                    error_messages = []
                    for row_num, error in result['failed_rows']:
                        error_messages.append(f"Row {row_num}: {error}")

                    # Limit the error message array to a reasonable length
                    if len(error_messages) > 5:
                        error_messages = error_messages[:5] + [f"... and {len(error_messages) - 5} more errors."]

                    for error in error_messages:
                        messages.warning(request, error)

                return redirect('member_list')

            except Exception as e:
                messages.error(request, f"Error during import: {str(e)}")
                return render(request, 'inventory/member/member_import.html', {'form': form})
    else:
        form = MemberImportForm()

    # Generate sample CSV data
    sample_data = [
        ['name', 'phone', 'email', 'member_id', 'level', 'points', 'birthday', 'address'],
        ['John Doe', '0987654321', 'john.doe@example.com', 'M202401001', 'Standard', '100', '1990-01-01', 'Hanoi'],
        ['Jane Smith', '0912345678', 'jane.smith@example.com', 'M202401002', 'Gold', '500', '1985-05-05', 'Ho Chi Minh City'],
    ]

    # Create in-memory CSV
    sample_csv = io.StringIO()
    writer = csv.writer(sample_csv)
    for row in sample_data:
        writer.writerow(row)

    sample_csv_content = sample_csv.getvalue()

    context = {
        'form': form,
        'sample_csv': sample_csv_content,
    }

    return render(request, 'inventory/member/member_import.html', context)


@login_required
def member_export(request):
    """Export members view"""
    # Get filter parameters
    filter_level = request.GET.get('level', '')
    is_active_filter = request.GET.get('status', '')

    # Base queryset
    members = Member.objects.select_related('level').all()

    # Apply filtering
    if filter_level:
        members = members.filter(level_id=filter_level)

    if is_active_filter == 'active':
        members = members.filter(is_active=True)
    elif is_active_filter == 'inactive':
        members = members.filter(is_active=False)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="members_export.csv"'

    # Write CSV
    writer = csv.writer(response)
    writer.writerow(['ID', 'Member ID', 'Name', 'Phone', 'Email', 'Member Level', 'Points', 'Birthday', 'Address', 'Notes', 'Status'])

    for member in members:
        writer.writerow([
            member.id,
            member.member_id,
            member.name,
            member.phone,
            member.email or '',
            member.level.name if member.level else '',
            member.points,
            member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            member.address or '',
            member.notes or '',
            'Active' if member.is_active else 'Inactive',
        ])

    return response


@login_required
def member_points_adjust(request, pk):
    """Adjust member points view"""
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        points_change = request.POST.get('points_change')
        description = request.POST.get('description', '')

        try:
            points_change = int(points_change)

            # Create points transaction record
            transaction = MemberTransaction.objects.create(
                member=member,
                transaction_type='POINTS_ADJUST',
                points_change=points_change,
                description=description,
                created_by=request.user
            )

            # Update member points
            member.points += points_change
            member.save()

            # Check if member level needs to be upgraded
            member_service.check_and_update_member_level(member)

            messages.success(request, f'Member points adjusted: {points_change:+d}')
            return redirect('member_detail', pk=member.id)

        except ValueError:
            messages.error(request, 'Points must be an integer')

    return render(request, 'inventory/member/points_adjust.html', {
        'member': member
    })


@login_required
def member_recharge(request, pk):
    """Member recharge view"""
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        actual_amount = Decimal(request.POST.get('actual_amount', '0'))
        payment_method = request.POST.get('payment_method', 'cash')
        remark = request.POST.get('remark', '')

        if amount <= 0:
            messages.error(request, 'Recharge amount must be greater than 0')
            return redirect('member_recharge', pk=pk)

        # Create recharge record
        recharge = RechargeRecord.objects.create(
            member=member,
            amount=amount,
            actual_amount=actual_amount,
            payment_method=payment_method,
            operator=request.user,
            remark=remark
        )

        # Create balance transaction record
        transaction = MemberTransaction.objects.create(
            member=member,
            transaction_type='RECHARGE',
            balance_change=amount,
            points_change=0,  # Recharge does not add points for now
            description=f'Member recharge - {dict(RechargeRecord.PAYMENT_CHOICES).get(payment_method, "Unknown")}',
            remark=remark,
            created_by=request.user
        )

        # Update member balance and status
        member.balance += amount
        member.is_recharged = True
        member.save()

        # Record operation log
        OperationLog.objects.create(
            operator=request.user,
            operation_type='MEMBER',
            details=f'Recharged member {member.name} amount {amount} VND',
            related_object_id=recharge.id,
            related_content_type=ContentType.objects.get_for_model(RechargeRecord)
        )

        messages.success(request, f'Successfully recharged {member.name} by {amount} VND')
        return redirect('member_detail', pk=member.pk)

    return render(request, 'inventory/member/member_recharge.html', {
        'member': member
    })


@login_required
def member_recharge_records(request, pk):
    """Member recharge records view"""
    member = get_object_or_404(Member, pk=pk)
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')

    return render(request, 'inventory/member/member_recharge_records.html', {
        'member': member,
        'recharge_records': recharge_records
    })


@login_required
def member_balance_adjust(request, pk):
    """Adjust member balance view"""
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        balance_change = request.POST.get('balance_change')
        description = request.POST.get('description', '')

        try:
            balance_change = Decimal(balance_change)

            # Create balance transaction record
            transaction = MemberTransaction.objects.create(
                member=member,
                transaction_type='BALANCE_ADJUST',
                balance_change=balance_change,
                description=description,
                created_by=request.user
            )

            # Update member balance
            member.balance += balance_change
            member.save()

            messages.success(request, f'Member balance adjusted: {balance_change:+.2f}')
            return redirect('member_detail', pk=member.id)

        except ValueError:
            messages.error(request, 'Balance must be a valid amount')

    return render(request, 'inventory/member/balance_adjust.html', {
        'member': member
    })


# Add alias function for backward compatibility
def member_edit(request, pk):
    """
    Alias of member_update for backward compatibility
    """
    return member_update(request, pk)


# Add more alias functions and missing features
def member_details(request, pk):
    """
    Alias of member_detail for backward compatibility
    """
    return member_detail(request, pk)

def member_level_edit(request, pk):
    """
    Alias of member_level_update for backward compatibility
    """
    return member_level_update(request, pk)

@login_required
def member_add_ajax(request):
    """
    View to add a member via AJAX.
    Used to quickly add members during the sales process.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')

        # Basic validation
        if not name or not phone:
            return JsonResponse({'success': False, 'message': 'Name and phone number are required'})

        # Validate if phone number already exists
        if Member.objects.filter(phone=phone).exists():
            return JsonResponse({'success': False, 'message': f'Phone number {phone} is already in use'})

        try:
            # Generate member ID
            current_date = datetime.now().strftime('%Y%m%d')
            random_suffix = str(uuid.uuid4().int)[:6]
            member_id = f'M{current_date}{random_suffix}'

            # Get default member level
            default_level = MemberLevel.objects.filter(is_active=True, is_default=True).first()
            if not default_level:
                default_level = MemberLevel.objects.filter(is_active=True).first()

            # Create member
            member = Member.objects.create(
                name=name,
                phone=phone,
                email=email,
                member_id=member_id,
                level=default_level,
                created_by=request.user
            )

            return JsonResponse({
                'success': True,
                'member_id': member.id,
                'member_name': member.name,
                'member_phone': member.phone,
                'member_level': member.level.name if member.level else '',
                'member_balance': float(member.balance),
                'member_points': member.points
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Failed to create member: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Only POST requests are supported'}) 