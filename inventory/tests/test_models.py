from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from inventory.models import (
    Category, 
    Product, 
    Inventory, 
    InventoryTransaction,
    Member,
    MemberLevel,
    Sale,
    SaleItem,
    RechargeRecord,
    InventoryCheck,
    InventoryCheckItem
)

class CategoryModelTest(TestCase):
    """Product category model tests"""
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
    def test_category_creation(self):
        """Test category creation"""
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(self.category.description, 'Test category description')
        self.assertTrue(self.category.created_at)
        self.assertTrue(self.category.updated_at)
    def test_category_str(self):
        """Test category string representation"""
        self.assertEqual(str(self.category), 'Test Category')

class ProductModelTest(TestCase):
    """Product model tests"""
    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='Test Product',
            category=self.category,
            description='Test product description',
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
    def test_product_creation(self):
        """Test product creation"""
        self.assertEqual(self.product.barcode, '1234567890')
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.description, 'Test product description')
        self.assertEqual(self.product.price, Decimal('10.00'))
        self.assertEqual(self.product.cost, Decimal('5.00'))
        self.assertTrue(self.product.created_at)
        self.assertTrue(self.product.updated_at)
    def test_product_str(self):
        """Test product string representation"""
        self.assertEqual(str(self.product), 'Test Product')

class InventoryModelTest(TestCase):
    """Inventory model tests"""
    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='Test Product',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10
        )
    def test_inventory_creation(self):
        """Test inventory creation"""
        self.assertEqual(self.inventory.product, self.product)
        self.assertEqual(self.inventory.quantity, 100)
        self.assertEqual(self.inventory.warning_level, 10)
        self.assertTrue(self.inventory.created_at)
        self.assertTrue(self.inventory.updated_at)
    def test_inventory_str(self):
        """Test inventory string representation"""
        self.assertEqual(str(self.inventory), f'{self.product.name} - 100')
    def test_is_low_stock(self):
        """Test inventory low stock property"""
        self.assertFalse(self.inventory.is_low_stock)
        self.inventory.quantity = 10
        self.inventory.save()
        self.assertTrue(self.inventory.is_low_stock)
        self.inventory.quantity = 5
        self.inventory.save()
        self.assertTrue(self.inventory.is_low_stock)

class InventoryTransactionModelTest(TestCase):
    """Inventory transaction model tests"""
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='Test Product',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        self.transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            quantity=50,
            operator=self.user,
            notes='Test stock in'
        )
    def test_transaction_creation(self):
        """Test transaction creation"""
        self.assertEqual(self.transaction.product, self.product)
        self.assertEqual(self.transaction.transaction_type, 'IN')
        self.assertEqual(self.transaction.quantity, 50)
        self.assertEqual(self.transaction.operator, self.user)
        self.assertEqual(self.transaction.notes, 'Test stock in')
        self.assertTrue(self.transaction.created_at)
    def test_transaction_str(self):
        """Test transaction string representation"""
        self.assertEqual(str(self.transaction), f'{self.product.name} - IN - 50')