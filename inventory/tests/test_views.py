from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from decimal import Decimal

from inventory.models import (
    Category, 
    Product, 
    Inventory, 
    InventoryTransaction,
    Member,
    MemberLevel,
    Sale,
    SaleItem
)

class ViewTestCase(TestCase):
    """Base class for view tests"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser', 
            password='12345',
            email='test@example.com'
        )
        # Create admin user
        self.admin = User.objects.create_user(
            username='admin', 
            password='admin123',
            email='admin@example.com',
            is_staff=True
        )
        # Create client
        self.client = Client()
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
            discount=95,  # 95%
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

class ProductViewTest(ViewTestCase):
    """Test product-related views"""
    
    def test_product_list_view(self):
        """Test product list view"""
        # Login
        self.client.login(username='testuser', password='12345')
        # Access product list page
        response = self.client.get(reverse('product_list'))
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/product_list.html')
        self.assertContains(response, 'Test Product')
    
    def test_product_create_view(self):
        """Test create product view"""
        self.client.login(username='testuser', password='12345')
        # Access create product page
        response = self.client.get(reverse('product_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/product_form.html')
        # Post create product form
        product_data = {
            'barcode': '9876543210',
            'name': 'New Test Product',
            'category': self.category.id,
            'description': 'New test product description',
            'price': '15.00',
            'cost': '7.50'
        }
        response = self.client.post(reverse('product_create'), product_data)
        # Assert redirect
        self.assertRedirects(response, reverse('product_list'))
        # Assert product created
        self.assertTrue(Product.objects.filter(barcode='9876543210').exists())

class InventoryViewTest(ViewTestCase):
    """Test inventory-related views"""
    
    def test_inventory_list_view(self):
        """Test inventory list view"""
        self.client.login(username='testuser', password='12345')
        # Access inventory list page
        response = self.client.get(reverse('inventory_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/inventory_list.html')
        self.assertContains(response, 'Test Product')
    
    def test_inventory_transaction_create_view(self):
        """Test create inventory transaction view"""
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('inventory_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/inventory_form.html')
        # Post create transaction form
        transaction_data = {
            'product': self.product.id,
            'quantity': '50',
            'notes': 'Test stock in'
        }
        response = self.client.post(reverse('inventory_create'), transaction_data)
        self.assertRedirects(response, reverse('inventory_list'))
        self.assertTrue(InventoryTransaction.objects.filter(product=self.product, quantity=50).exists())
        # Refresh inventory object
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 150)  # 100 + 50

class SaleViewTest(ViewTestCase):
    """Test sale-related views"""
    def test_sale_list_view(self):
        """Test sale list view"""
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('sale_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sale_list.html')
    def test_sale_create_view(self):
        """Test create sale view"""
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('sale_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sale_form.html')
        sale_data = {
            'payment_method': 'cash',
            'member': self.member.id
        }
        response = self.client.post(reverse('sale_create'), sale_data)
        self.assertTrue(Sale.objects.filter(member=self.member).exists())
        sale = Sale.objects.filter(member=self.member).first()
        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))