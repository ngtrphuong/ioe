"""
Permission handling module for the inventory system.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models

# Import decorators
from .decorators import (
    permission_required, 
    group_required, 
    superuser_required, 
    owner_or_permission_required,
    system_admin_required
)

# Export decorators
__all__ = [
    'permission_required', 
    'group_required', 
    'superuser_required', 
    'owner_or_permission_required',
    'system_admin_required',
    'setup_permissions',
]

# Define common permission codenames
PERMISSIONS = {
    # Inventory permissions
    'view_inventory': 'View Inventory',
    'change_inventory': 'Change Inventory',
    'add_inventory': 'Add Inventory',
    
    # Product permissions
    'view_product': 'View Product',
    'add_product': 'Add Product',
    'change_product': 'Change Product',
    'delete_product': 'Delete Product',
    
    # Sales permissions
    'view_sale': 'View Sale',
    'add_sale': 'Add Sale',
    'void_sale': 'Void Sale',
    
    # Member permissions
    'view_member': 'View Member',
    'add_member': 'Add Member',
    'change_member': 'Change Member',
    
    # Report permissions
    'view_reports': 'View Reports',
    'export_reports': 'Export Reports',
    
    # Inventory check permissions
    'perform_inventory_check': 'Perform Inventory Check',
    'approve_inventory_check': 'Approve Inventory Check',
}

# Define role-permission mappings
ROLES = {
    'admin': {
        'name': 'System Administrator',
        'permissions': list(PERMISSIONS.keys()),
    },
    'manager': {
        'name': 'Store Manager',
        'permissions': [
            'view_inventory', 'change_inventory', 'add_inventory',
            'view_product', 'add_product', 'change_product',
            'view_sale', 'add_sale', 'void_sale',
            'view_member', 'add_member', 'change_member',
            'view_reports', 'export_reports',
            'perform_inventory_check', 'approve_inventory_check',
        ],
    },
    'sales': {
        'name': 'Sales Clerk',
        'permissions': [
            'view_inventory',
            'view_product',
            'view_sale', 'add_sale',
            'view_member', 'add_member',
        ],
    },
    'inventory': {
        'name': 'Inventory Manager',
        'permissions': [
            'view_inventory', 'change_inventory', 'add_inventory',
            'view_product', 'add_product', 'change_product',
            'perform_inventory_check',
        ],
    },
}

def setup_permissions():
    """Set up all permissions and groups."""
    # Create all custom permissions
    for model in [
        'inventory', 'product', 'sale', 'member', 'report', 'inventorycheck'
    ]:
        content_type = ContentType.objects.get_for_model(models.Model)
        for codename, name in PERMISSIONS.items():
            if codename.split('_')[1] == model:
                Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )

    # Create groups and assign permissions
    for role_key, role_info in ROLES.items():
        group, created = Group.objects.get_or_create(name=role_info['name'])
        # Get all permissions for this role
        permissions = Permission.objects.filter(codename__in=role_info['permissions'])
        # Assign permissions to group
        group.permissions.set(permissions) 