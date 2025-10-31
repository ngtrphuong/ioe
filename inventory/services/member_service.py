"""
Member service module - business logic for member management
"""
import csv
import io
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from ..models import Member, MemberLevel, MemberTransaction


def check_and_update_member_level(member):
    """
    Check member points and update member level accordingly. Automatically upgrade member level if new threshold reached.
    """
    # Get member's current level
    current_level = member.level
    
    # Get all potential higher levels
    higher_levels = MemberLevel.objects.filter(
        points_threshold__lte=member.points,
    )
    highest_eligible_level = None
    if higher_levels.exists():
        highest_eligible_level = higher_levels.first()
        # If there is a higher level, and it's not the current level, then upgrade
        if highest_eligible_level != current_level:
            old_level_name = current_level.name if current_level else "No level"
            # Record member level change
            MemberTransaction.objects.create(
                member=member,
                transaction_type='LEVEL_UPGRADE',
                description=f'Level changed from {old_level_name} to {highest_eligible_level.name}',
                points=member.points,
                operator=member.created_by  # Use the creator of the member as the operator
            )
            # Update member level
            member.level = highest_eligible_level
            member.save(update_fields=['level', 'updated_at'])
            
            return True, old_level_name, highest_eligible_level.name
    
    return False, None, None


def import_members_from_csv(csv_file, operator):
    """
    Import member data from a CSV file.

    Parameters:
    - csv_file: Uploaded CSV file
    - operator: User performing the import

    Returns:
    - dict: Dictionary containing import results
    """
    # Reset file pointer
    csv_file.seek(0)
    
    # Read CSV file
    csv_data = csv_file.read().decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    success_count = 0
    skipped_count = 0
    failed_count = 0
    failed_rows = []
    
    # Get default member level
    default_level = MemberLevel.objects.filter(is_default=True, is_active=True).first()
    if not default_level:
        default_level = MemberLevel.objects.filter(is_active=True).first()
    
    # Begin import
    for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
        try:
            with transaction.atomic():
                # Check required fields
                if not row.get('name') or not row.get('phone'):
                    failed_rows.append((row_num, "Name and phone number are required"))
                    failed_count += 1
                    continue
                
                # Check if phone number already exists
                if Member.objects.filter(phone=row.get('phone')).exists():
                    skipped_count += 1
                    continue
                
                # Handle member level
                level = default_level
                if row.get('level'):
                    try:
                        level_obj = MemberLevel.objects.get(name=row.get('level'))
                        level = level_obj
                    except MemberLevel.DoesNotExist:
                        pass  # Use default level
                
                # Handle birthday
                birthday = None
                if row.get('birthday'):
                    try:
                        birthday = datetime.strptime(row.get('birthday'), '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                # Handle points
                points = 0
                if row.get('points'):
                    try:
                        points = int(row.get('points'))
                    except ValueError:
                        points = 0
                
                # Create member
                member = Member.objects.create(
                    name=row.get('name'),
                    phone=row.get('phone'),
                    email=row.get('email', ''),
                    member_id=row.get('member_id', ''),
                    level=level,
                    points=points,
                    birthday=birthday,
                    address=row.get('address', ''),
                    created_by=operator
                )
                
                success_count += 1
                
        except Exception as e:
            failed_count += 1
            failed_rows.append((row_num, str(e)))
    
    return {
        'success': success_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'failed_rows': failed_rows
    }


def get_member_statistics():
    """
    Get member statistics.

    Returns:
    - dict: Dictionary containing member statistics
    """
    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()
    
    # Count members per level
    level_stats = []
    for level in MemberLevel.objects.filter(is_active=True):
        level_count = Member.objects.filter(level=level).count()
        if level_count > 0:
            level_stats.append({
                'level_name': level.name,
                'level_color': level.color,
                'count': level_count,
                'percentage': round(level_count / total_members * 100 if total_members > 0 else 0, 2)
            })
    
    # Members added this month
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_members_this_month = Member.objects.filter(created_at__gte=current_month_start).count()
    
    return {
        'total_members': total_members,
        'active_members': active_members,
        'inactive_members': total_members - active_members,
        'level_stats': level_stats,
        'new_members_this_month': new_members_this_month,
    } 