from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from faker import Faker
import datetime

from inventory.models.product import Product, Category, Store
from inventory.models.member import Member, MemberLevel
from inventory.models.sales import Sale, SaleItem
from inventory.models.inventory import Inventory

fake = Faker('vi_VN')

class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu cho hệ thống quản lý kho hàng Mẹ & Bé'

    def add_arguments(self, parser):
        parser.add_argument('--categories', type=int, default=10, help='Số lượng danh mục sản phẩm')
        parser.add_argument('--products', type=int, default=100, help='Số lượng sản phẩm')
        parser.add_argument('--members', type=int, default=30, help='Số lượng thành viên')
        parser.add_argument('--sales', type=int, default=50, help='Số lượng bản ghi bán hàng')
        parser.add_argument('--clean', action='store_true', help='Xóa dữ liệu hiện có trước khi tạo mới')

    def handle(self, *args, **options):
        num_categories = options['categories']
        num_products = options['products']
        num_members = options['members']
        num_sales = options['sales']
        clean = options['clean']

        if clean:
            self.clean_database()
            self.stdout.write(self.style.SUCCESS('Đã xóa dữ liệu hiện có'))

        try:
            with transaction.atomic():
                # Đảm bảo có người dùng quản trị
                admin_user, created = User.objects.get_or_create(
                    username='admin',
                    defaults={
                        'is_staff': True,
                        'is_superuser': True,
                        'email': 'admin@example.com',
                    }
                )
                if created:
                    admin_user.set_password('admin')
                    admin_user.save()
                    self.stdout.write(self.style.SUCCESS('Đã tạo người dùng quản trị'))

                # Tạo cấp độ thành viên
                levels = self.create_member_levels()
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(levels)} cấp độ thành viên'))

                # Tạo danh mục sản phẩm
                categories = self.create_categories(num_categories)
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(categories)} danh mục sản phẩm'))

                # Tạo sản phẩm
                products = self.create_products(categories, num_products)
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(products)} sản phẩm'))

                # Tạo thành viên
                members = self.create_members(levels, num_members, admin_user)
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(members)} thành viên'))

                # Tạo bản ghi bán hàng
                sales = self.create_sales(products, members, num_sales, admin_user)
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(sales)} bản ghi bán hàng'))

                self.stdout.write(self.style.SUCCESS('Hoàn thành tạo dữ liệu mẫu!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Lỗi khi tạo dữ liệu mẫu: {e}'))

    def clean_database(self):
        """Xóa dữ liệu hiện có"""
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        
        # Xóa tất cả bản ghi thành viên, không chỉ thành viên thử nghiệm
        Member.objects.all().delete()
        User.objects.filter(username__startswith='member_').delete()
        
        # Xóa các bản ghi liên quan đến Product trước
        from inventory.models.inventory import InventoryTransaction
        from inventory.models.inventory_check import InventoryCheckItem
        InventoryTransaction.objects.all().delete()
        InventoryCheckItem.objects.all().delete()
        
        Inventory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        MemberLevel.objects.all().delete()

    def create_member_levels(self):
        """Tạo cấp độ thành viên cho cửa hàng Mẹ & Bé"""
        levels_data = [
            {'name': 'Thành viên mới', 'discount': Decimal('0.95'), 'points_threshold': 0, 'color': '#808080', 'priority': 1, 'is_default': True},
            {'name': 'Thành viên thân thiết', 'discount': Decimal('0.90'), 'points_threshold': 1000, 'color': '#C0C0C0', 'priority': 2},
            {'name': 'Thành viên VIP', 'discount': Decimal('0.85'), 'points_threshold': 3000, 'color': '#FFD700', 'priority': 3},
            {'name': 'Thành viên Kim cương', 'discount': Decimal('0.80'), 'points_threshold': 10000, 'color': '#B9F2FF', 'priority': 4},
        ]
        
        levels = []
        for data in levels_data:
            level, created = MemberLevel.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            levels.append(level)
        return levels

    def create_categories(self, num_categories):
        """Tạo danh mục sản phẩm cho cửa hàng Mẹ & Bé"""
        category_names = [
            'Đồ dùng cho mẹ', 'Đồ dùng cho bé', 'Thực phẩm dinh dưỡng', 'Quần áo trẻ em', 
            'Đồ chơi giáo dục', 'Sản phẩm chăm sóc', 'Đồ dùng vệ sinh', 'Đồ dùng ăn uống',
            'Đồ dùng ngủ', 'Đồ dùng tắm', 'Đồ dùng đi lại', 'Sách và học liệu',
            'Đồ dùng y tế', 'Sản phẩm an toàn', 'Đồ dùng ngoài trời'
        ]
        
        categories = []
        for i in range(min(num_categories, len(category_names))):
            name = category_names[i]
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'Sản phẩm thuộc danh mục {name}',
                    'is_active': True,
                }
            )
            categories.append(category)
        return categories

    def create_products(self, categories, num_products):
        """Tạo sản phẩm cho cửa hàng Mẹ & Bé"""
        products = []
        colors = ['Đỏ', 'Xanh dương', 'Đen', 'Trắng', 'Xám', 'Xanh lá', 'Vàng', 'Tím', 'Hồng', 'Cam']
        sizes = ['S', 'M', 'L', 'XL', 'XXL', 'Đều', '0-3M', '3-6M', '6-9M', '9-12M', '12-18M', '18-24M', '2T', '3T', '4T']
        
        # Danh sách thương hiệu và sản phẩm cho Mẹ & Bé
        mom_baby_brands = {
            'Đồ dùng cho mẹ': ['Pigeon', 'Medela', 'Lansinoh', 'Philips Avent', 'Chicco', 'Combi'],
            'Đồ dùng cho bé': ['Pigeon', 'Chicco', 'Combi', 'Fisher-Price', 'VTech', 'Skip Hop'],
            'Thực phẩm dinh dưỡng': ['Nestle', 'Abbott', 'Friso', 'Meiji', 'Wakodo', 'HiPP'],
            'Quần áo trẻ em': ['Carter\'s', 'Gap Kids', 'H&M Kids', 'Zara Kids', 'Uniqlo Kids', 'Next'],
            'Đồ chơi giáo dục': ['Fisher-Price', 'VTech', 'LeapFrog', 'Melissa & Doug', 'Hape', 'Plan Toys'],
            'Sản phẩm chăm sóc': ['Johnson\'s', 'Aveeno', 'Cetaphil', 'Mustela', 'Weleda', 'Burt\'s Bees'],
            'Đồ dùng vệ sinh': ['Pampers', 'Huggies', 'Merries', 'Goo.N', 'Moony', 'Bambo Nature'],
            'Đồ dùng ăn uống': ['Pigeon', 'Chicco', 'Philips Avent', 'Nuk', 'Dr. Brown\'s', 'Tommee Tippee'],
            'Đồ dùng ngủ': ['Fisher-Price', 'Summer Infant', 'Graco', 'Chicco', 'Skip Hop', '4moms'],
            'Đồ dùng tắm': ['Pigeon', 'Chicco', 'Summer Infant', 'Fisher-Price', 'Skip Hop', '4moms'],
            'Đồ dùng đi lại': ['Chicco', 'Graco', 'Britax', 'Cybex', 'Uppababy', 'Baby Jogger'],
            'Sách và học liệu': ['Fisher-Price', 'VTech', 'LeapFrog', 'Melissa & Doug', 'Hape', 'Plan Toys'],
            'Đồ dùng y tế': ['Braun', 'Omron', 'Philips Avent', 'Chicco', 'Pigeon', 'Summer Infant'],
            'Sản phẩm an toàn': ['Summer Infant', 'Safety 1st', 'Chicco', 'Graco', 'Fisher-Price', 'Skip Hop'],
            'Đồ dùng ngoài trời': ['Fisher-Price', 'Step2', 'Little Tikes', 'Radio Flyer', 'Hape', 'Plan Toys']
        }
        
        for i in range(num_products):
            category = random.choice(categories)
            # Điều chỉnh giá cho thị trường Việt Nam (VND)
            price = Decimal(str(round(random.uniform(50000, 2000000), 0)))  # 50k - 2M VND
            cost = price * Decimal(str(round(random.uniform(0.5, 0.8), 2)))
            
            barcode = f'893{random.randint(10000000, 99999999)}'  # Mã vạch Việt Nam
            
            # Tạo tên sản phẩm dựa trên danh mục
            if category.name in mom_baby_brands:
                brand = random.choice(mom_baby_brands[category.name])
                product_types = self.get_product_types_for_category(category.name)
                product_type = random.choice(product_types)
                name = f"{brand} {product_type}"
            else:
                name = f"Sản phẩm {category.name} {i+1}"
            
            color = random.choice(colors)
            size = random.choice(sizes)
            
            product, created = Product.objects.get_or_create(
                barcode=barcode,
                defaults={
                    'name': name,
                    'category': category,
                    'description': f'Sản phẩm chất lượng cao cho {category.name}',
                    'price': price,
                    'cost': cost,
                    'specification': f'{random.choice(["Tiêu chuẩn", "Cao cấp", "Tiết kiệm", "Premium"])}',
                    'manufacturer': brand if category.name in mom_baby_brands else fake.company(),
                    'color': color,
                    'size': size,
                    'is_active': True,
                }
            )
            
            if created:
                # Create inventory
                inventory, _ = Inventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'quantity': random.randint(10, 100),
                        'warning_level': random.randint(5, 15),
                    }
                )
                products.append(product)
        
        return products

    def get_product_types_for_category(self, category_name):
        """Lấy danh sách loại sản phẩm cho từng danh mục"""
        product_types = {
            'Đồ dùng cho mẹ': ['Máy hút sữa', 'Bình sữa', 'Áo ngực cho con bú', 'Miếng lót thấm sữa', 'Kem chống nứt núm vú'],
            'Đồ dùng cho bé': ['Bình sữa', 'Núm vú', 'Bình nước', 'Cốc tập uống', 'Yếm ăn'],
            'Thực phẩm dinh dưỡng': ['Sữa công thức', 'Bột ăn dặm', 'Bánh ăn dặm', 'Nước ép trái cây', 'Thực phẩm bổ sung'],
            'Quần áo trẻ em': ['Áo sơ mi', 'Quần dài', 'Váy', 'Áo khoác', 'Đồ ngủ', 'Tất'],
            'Đồ chơi giáo dục': ['Xếp hình', 'Đồ chơi âm nhạc', 'Sách vải', 'Đồ chơi phát triển trí tuệ', 'Búp bê'],
            'Sản phẩm chăm sóc': ['Sữa tắm', 'Dầu gội', 'Kem dưỡng da', 'Phấn rôm', 'Kem chống nắng'],
            'Đồ dùng vệ sinh': ['Tã giấy', 'Khăn ướt', 'Bỉm vải', 'Tã quần', 'Khăn tắm'],
            'Đồ dùng ăn uống': ['Bát ăn', 'Thìa', 'Nĩa', 'Cốc', 'Đĩa', 'Khay ăn'],
            'Đồ dùng ngủ': ['Nôi', 'Chăn', 'Gối', 'Đệm', 'Màn chống muỗi'],
            'Đồ dùng tắm': ['Chậu tắm', 'Ghế tắm', 'Khăn tắm', 'Xà phòng', 'Dầu gội'],
            'Đồ dùng đi lại': ['Xe đẩy', 'Xe tập đi', 'Địu', 'Ghế ngồi ô tô', 'Xe đạp 3 bánh'],
            'Sách và học liệu': ['Sách tranh', 'Sách tô màu', 'Flashcard', 'Bảng chữ cái', 'Sách số'],
            'Đồ dùng y tế': ['Nhiệt kế', 'Máy hút mũi', 'Băng dán', 'Thuốc mỡ', 'Dụng cụ vệ sinh'],
            'Sản phẩm an toàn': ['Cổng an toàn', 'Khóa tủ', 'Nút bịt ổ cắm', 'Miếng dán góc', 'Đai an toàn'],
            'Đồ dùng ngoài trời': ['Xích đu', 'Cầu trượt', 'Bể bơi phao', 'Xe đạp', 'Đồ chơi cát']
        }
        return product_types.get(category_name, ['Sản phẩm', 'Đồ dùng', 'Vật dụng'])

    def create_members(self, levels, num_members, admin_user):
        """Tạo thành viên cho cửa hàng Mẹ & Bé"""
        members = []
        gender_choices = ['F', 'M', 'O']  # Ưu tiên nữ cho thị trường Mẹ & Bé
        vietnamese_names = [
            'Nguyễn Thị Hương', 'Trần Thị Mai', 'Lê Thị Lan', 'Phạm Thị Hoa', 'Hoàng Thị Linh',
            'Vũ Thị Nga', 'Đặng Thị Thu', 'Bùi Thị Hạnh', 'Đỗ Thị Minh', 'Hồ Thị Anh',
            'Nguyễn Văn Nam', 'Trần Văn Hùng', 'Lê Văn Đức', 'Phạm Văn Tài', 'Hoàng Văn Minh',
            'Vũ Văn Long', 'Đặng Văn Quang', 'Bùi Văn Thành', 'Đỗ Văn Huy', 'Hồ Văn Dũng'
        ]
        
        for i in range(num_members):
            username = f'member_{i+1}'
            # Kiểm tra người dùng đã tồn tại
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': fake.email(),
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'is_staff': False,
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('password')
                user.save()
            
            # Chọn cấp độ thành viên phù hợp dựa trên điểm
            points = random.randint(0, 15000)
            suitable_level = levels[0]  # Mặc định là cấp thấp nhất
            
            for level in levels:
                if points >= level.points_threshold:
                    if level.priority > suitable_level.priority:
                        suitable_level = level
            
            # Sử dụng tên Việt Nam
            member_name = random.choice(vietnamese_names)
            
            member, created = Member.objects.get_or_create(
                user=user,
                defaults={
                    'name': member_name,
                    'phone': fake.phone_number(),
                    'gender': random.choice(gender_choices),
                    'birthday': fake.date_of_birth(minimum_age=20, maximum_age=45),  # Tuổi phù hợp cho mẹ
                    'level': suitable_level,
                    'points': points,
                    'total_spend': Decimal(str(random.randint(0, 50000000))),  # VND
                    'purchase_count': random.randint(0, 30),
                    'balance': Decimal(str(random.randint(0, 1000000))),  # VND
                    'is_recharged': random.choice([True, False]),
                    'member_id': f'M{random.randint(100000, 999999)}',
                    'email': fake.email(),
                    'address': fake.address(),
                    'notes': 'Thành viên được tạo tự động',
                    'is_active': True,
                    'created_by': admin_user,
                    'updated_by': admin_user,
                }
            )
            
            if created:
                members.append(member)
        
        return members

    def create_sales(self, products, members, num_sales, admin_user):
        """Tạo bản ghi bán hàng cho cửa hàng Mẹ & Bé"""
        sales = []
        payment_methods = ['cash', 'bank_transfer', 'momo', 'zalopay', 'vnpay', 'credit_card']
        
        # Tạo dữ liệu bán hàng trong 6 tháng qua
        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=180)
        
        for i in range(num_sales):
            # Ngày bán hàng ngẫu nhiên
            sale_date = start_date + datetime.timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )
            
            # Chọn ngẫu nhiên thành viên hoặc không có thành viên
            member = random.choice([None] + members) if random.random() < 0.8 else None
            
            # Tạo bản ghi bán hàng
            sale = Sale.objects.create(
                member=member,
                total_amount=Decimal('0.00'),  # Sẽ cập nhật sau
                discount_amount=Decimal('0.00'),  # Sẽ cập nhật sau
                final_amount=Decimal('0.00'),  # Sẽ cập nhật sau
                payment_method=random.choice(payment_methods),
                operator=admin_user,
                remark='Bản ghi bán hàng được tạo tự động'
            )
            
            # Thêm 1 đến 5 sản phẩm vào bản ghi bán hàng
            num_items = random.randint(1, 5)
            sale_products = random.sample(products, min(num_items, len(products)))
            
            for product in sale_products:
                quantity = random.randint(1, 3)
                price = product.price
                
                # Áp dụng giảm giá thành viên
                actual_price = price
                if member:
                    actual_price = price * member.level.discount
                
                # Tạo mục bán hàng
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    price=price,
                    actual_price=actual_price,
                )
            
            # Cập nhật tổng số tiền bán hàng
            sale.update_total_amount()
            
            # Tính số tiền giảm giá dựa trên cấp độ thành viên
            if member:
                discount_rate = 1 - member.level.discount
                sale.discount_amount = sale.total_amount * discount_rate
                sale.final_amount = sale.total_amount - sale.discount_amount
                sale.save()
                
                # Cộng dồn điểm và thông tin chi tiêu của thành viên
                points_earned = int(sale.final_amount / 1000)  # 1 điểm cho mỗi 1000 VND
                sale.points_earned = points_earned
                sale.save()
                
                member.points += points_earned
                member.total_spend += sale.final_amount
                member.purchase_count += 1
                
                # Kiểm tra xem có cần nâng cấp cấp độ thành viên không
                current_level = member.level
                available_levels = MemberLevel.objects.filter(
                    points_threshold__lte=member.points
                ).order_by('-priority')
                
                if available_levels.exists() and available_levels.first().priority > current_level.priority:
                    member.level = available_levels.first()
                
                member.save()
            
            sales.append(sale)
        
        return sales 