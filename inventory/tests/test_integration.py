from django.test import TestCase, Client
from django.urls import reverse
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
    InventoryCheck,
    InventoryCheckItem
)

class IntegrationTestCase(TestCase):
    """Base class for integration tests"""
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser', 
            password='12345',
            email='test@example.com'
        )
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='12345')
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        # Create test product
        self.product = Product.objects.create(
            barcode='1234567890',
            name='Test Product',
            category=self.category,
            description='Test product description',
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        # Create inventory record
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10
        )
        # Create member level
        self.member_level = MemberLevel.objects.create(
            name='Regular Member',
            discount=95,
            points_threshold=0,
            color='#FF5733'
        )
        # Create member
        self.member = Member.objects.create(
            name='Test Member',
            phone='13800138000',
            level=self.member_level,
            balance=Decimal('100.00'),
            points=0
        )

class SaleProcessTest(IntegrationTestCase):
    """Test full sales process"""
    def test_complete_sale_process(self):
        """Test from creating sale to adding sale item end-to-end"""
        # 1. Create sale
        sale_data = {
            'payment_method': 'cash',
            'member': self.member.id
        }
        response = self.client.post(reverse('sale_create'), sale_data)
        self.assertEqual(response.status_code, 302)  # redirect
        # Get created sale
        sale = Sale.objects.filter(member=self.member).first()
        self.assertIsNotNone(sale)
        # 2. Add sale item
        sale_item_data = {
            'product': self.product.id,
            'quantity': 5,
            'price': self.product.price
        }
        response = self.client.post(
            reverse('sale_item_create', args=[sale.id]), 
            sale_item_data
        )
        self.assertEqual(response.status_code, 302)  # redirect
        sale_item = SaleItem.objects.filter(sale=sale, product=self.product).first()
        self.assertIsNotNone(sale_item)
        self.assertEqual(sale_item.quantity, 5)
        # Inventory reduced
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)  # 100 - 5
        # Transaction created
        transaction = InventoryTransaction.objects.filter(
            product=self.product,
            transaction_type='OUT',
            quantity=5
        ).first()
        self.assertIsNotNone(transaction)
        # Sale amount updated
        sale.refresh_from_db()
        expected_amount = Decimal('50.00')
        self.assertEqual(sale.total_amount, expected_amount)

class InventoryCheckProcessTest(IntegrationTestCase):
    """Test full inventory check process"""
    def test_complete_inventory_check_process(self):
        """Test from creating inventory check to completing check end-to-end"""
        # 1. Create inventory check
        check_data = {
            'name': 'Test Check',
            'description': 'Test check description'
        }
        response = self.client.post(reverse('inventory_check_create'), check_data)
        self.assertEqual(response.status_code, 302)  # redirect
        inventory_check = InventoryCheck.objects.filter(name='Test Check').first()
        self.assertIsNotNone(inventory_check)
        self.assertEqual(inventory_check.status, 'draft')
        # Check item created
        check_item = InventoryCheckItem.objects.filter(
            inventory_check=inventory_check,
            product=self.product
        ).first()
        self.assertIsNotNone(check_item)
        self.assertEqual(check_item.system_quantity, 100)
        # 2. Start inventory check
        response = self.client.post(reverse('inventory_check_start', args=[inventory_check.id]))
        self.assertEqual(response.status_code, 302)
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'in_progress')
        # 3. Record check result
        item_data = {
            'actual_quantity': 95,
            'notes': 'Test inventory check record'
        }
        response = self.client.post(
            reverse('inventory_check_item_update', args=[inventory_check.id, check_item.id]),
            item_data
        )
        self.assertEqual(response.status_code, 302)
        check_item.refresh_from_db()
        self.assertEqual(check_item.actual_quantity, 95)
        self.assertEqual(check_item.notes, 'Test inventory check record')
        # 4. Complete check
        response = self.client.post(reverse('inventory_check_complete', args=[inventory_check.id]))
        self.assertEqual(response.status_code, 302)
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'completed')
        # 5. Approve check and adjust inventory
        approve_data = {
            'adjust_inventory': True
        }
        response = self.client.post(
            reverse('inventory_check_approve', args=[inventory_check.id]),
            approve_data
        )
        self.assertEqual(response.status_code, 302)
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'approved')
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)  # Adjusted to actual quantity