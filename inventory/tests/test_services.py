from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

from inventory.models import (
    Category, 
    Product, 
    Inventory, 
    InventoryTransaction,
    InventoryCheck,
    InventoryCheckItem
)
from inventory.services.inventory_service import InventoryService
from inventory.services.inventory_check_service import InventoryCheckService
from inventory.exceptions import InsufficientStockError, InventoryValidationError

class InventoryServiceTest(TestCase):
    """Inventory service tests"""
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='12345')
        # Create test category
        self.category = Category.objects.create(name='Test Category')
        # Create test product
        self.product = Product.objects.create(
            barcode='1234567890',
            name='Test Product',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        # Create inventory record
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10
        )
    def test_check_stock(self):
        """Test check_stock method"""
        self.assertTrue(InventoryService.check_stock(self.product, 50))
        self.assertTrue(InventoryService.check_stock(self.product, 100))
        self.assertFalse(InventoryService.check_stock(self.product, 150))
    def test_update_stock_in(self):
        """Test stock IN operation"""
        inventory, transaction = InventoryService.update_stock(
            product=self.product,
            quantity=50,
            transaction_type='IN',
            operator=self.user,
            notes='Test stock in'
        )
        self.assertEqual(inventory.quantity, 150)  # 100 + 50
        self.assertEqual(transaction.product, self.product)
        self.assertEqual(transaction.transaction_type, 'IN')
        self.assertEqual(transaction.quantity, 50)
        self.assertEqual(transaction.operator, self.user)
        self.assertEqual(transaction.notes, 'Test stock in')
    def test_update_stock_out(self):
        """Test stock OUT operation"""
        inventory, transaction = InventoryService.update_stock(
            product=self.product,
            quantity=30,
            transaction_type='OUT',
            operator=self.user,
            notes='Test stock out'
        )
        self.assertEqual(inventory.quantity, 70)  # 100 - 30
        self.assertEqual(transaction.product, self.product)
        self.assertEqual(transaction.transaction_type, 'OUT')
        self.assertEqual(transaction.quantity, 30)
        self.assertEqual(transaction.operator, self.user)
        self.assertEqual(transaction.notes, 'Test stock out')
    def test_update_stock_out_insufficient(self):
        """Test OUT operation with insufficient stock"""
        with self.assertRaises(InsufficientStockError):
            InventoryService.update_stock(
                product=self.product,
                quantity=150,  # greater than available
                transaction_type='OUT',
                operator=self.user,
                notes='Test stock out failure'
            )
    def test_update_stock_adjust(self):
        """Test stock ADJUST operation"""
        inventory, transaction = InventoryService.update_stock(
            product=self.product,
            quantity=80,
            transaction_type='ADJUST',
            operator=self.user,
            notes='Test adjust'
        )
        self.assertEqual(inventory.quantity, 80)
        self.assertEqual(transaction.product, self.product)
        self.assertEqual(transaction.transaction_type, 'ADJUST')
        self.assertEqual(transaction.quantity, 80)
        self.assertEqual(transaction.operator, self.user)
        self.assertEqual(transaction.notes, 'Test adjust')
    def test_get_low_stock_items(self):
        """Test getting low stock items"""
        # Initially, there should be no low stock items
        low_stock_items = InventoryService.get_low_stock_items()
        self.assertEqual(low_stock_items.count(), 0)
        # Set inventory to warning level
        self.inventory.quantity = 10
        self.inventory.save()
        low_stock_items = InventoryService.get_low_stock_items()
        self.assertEqual(low_stock_items.count(), 1)
        self.assertEqual(low_stock_items.first(), self.inventory)
        # Lower inventory below warning
        self.inventory.quantity = 5
        self.inventory.save()
        low_stock_items = InventoryService.get_low_stock_items()
        self.assertEqual(low_stock_items.count(), 1)
        self.assertEqual(low_stock_items.first(), self.inventory)

class InventoryCheckServiceTest(TestCase):
    """Inventory check service tests"""
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Test Category')
        self.product1 = Product.objects.create(
            barcode='1234567890',
            name='Test Product 1',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        self.product2 = Product.objects.create(
            barcode='0987654321',
            name='Test Product 2',
            category=self.category,
            price=Decimal('20.00'),
            cost=Decimal('10.00')
        )
        self.inventory1 = Inventory.objects.create(
            product=self.product1,
            quantity=100,
            warning_level=10
        )
        self.inventory2 = Inventory.objects.create(
            product=self.product2,
            quantity=50,
            warning_level=5
        )
    def test_create_inventory_check(self):
        """Test create inventory check"""
        inventory_check = InventoryCheckService.create_inventory_check(
            name='Test Check',
            description='Test check description',
            user=self.user
        )
        self.assertEqual(inventory_check.name, 'Test Check')
        self.assertEqual(inventory_check.description, 'Test check description')
        self.assertEqual(inventory_check.status, 'draft')
        self.assertEqual(inventory_check.created_by, self.user)
        self.assertEqual(inventory_check.items.count(), 2)  # two products
        item1 = inventory_check.items.get(product=self.product1)
        self.assertEqual(item1.system_quantity, 100)
        self.assertIsNone(item1.actual_quantity)
        item2 = inventory_check.items.get(product=self.product2)
        self.assertEqual(item2.system_quantity, 50)
        self.assertIsNone(item2.actual_quantity)
    def test_start_inventory_check(self):
        """Test start inventory check"""
        inventory_check = InventoryCheckService.create_inventory_check(
            name='Test Check',
            description='Test check description',
            user=self.user
        )
        updated_check = InventoryCheckService.start_inventory_check(
            inventory_check=inventory_check,
            user=self.user
        )
        self.assertEqual(updated_check.status, 'in_progress')
    def test_record_check_item(self):
        """Test record inventory check item"""
        inventory_check = InventoryCheckService.create_inventory_check(
            name='Test Check',
            description='Test check description',
            user=self.user
        )
        inventory_check = InventoryCheckService.start_inventory_check(
            inventory_check=inventory_check,
            user=self.user
        )
        check_item = inventory_check.items.get(product=self.product1)
        updated_item = InventoryCheckService.record_check_item(
            inventory_check_item=check_item,
            actual_quantity=90,  # actual differs from system
            user=self.user,
            notes='Test check record'
        )
        self.assertEqual(updated_item.actual_quantity, 90)
        self.assertEqual(updated_item.notes, 'Test check record')
        self.assertEqual(updated_item.checked_by, self.user)
        self.assertIsNotNone(updated_item.checked_at)