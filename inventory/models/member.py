from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class MemberLevel(models.Model):
    """Member Level Model, defines different member levels and their discount benefits"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Level Name')
    discount = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Discount Rate'
    )
    points_threshold = models.IntegerField(verbose_name='Points Required for Upgrade')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    color = models.CharField(max_length=50, default='blue', verbose_name='Color Identifier')
    priority = models.IntegerField(default=0, verbose_name='Priority')
    is_default = models.BooleanField(default=False, verbose_name='Is Default Level')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')

    class Meta:
        verbose_name = 'Member Level'
        verbose_name_plural = 'Member Levels'
        ordering = ['priority', 'points_threshold']

    def __str__(self):
        return self.name


class Member(models.Model):
    """Member Model, stores member basic information and consumption statistics"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User', null=True, blank=True)
    level = models.ForeignKey(MemberLevel, on_delete=models.PROTECT, verbose_name='Member Level')
    name = models.CharField(max_length=100, verbose_name='Name')
    phone = models.CharField(max_length=20, unique=True, verbose_name='Phone Number')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='Gender', default='O')
    birthday = models.DateField(null=True, blank=True, verbose_name='Birthday')
    points = models.IntegerField(default=0, verbose_name='Points')
    total_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Total Spending')
    purchase_count = models.IntegerField(default=0, verbose_name='Purchase Count')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registration Time')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Account Balance')
    is_recharged = models.BooleanField(default=False, verbose_name='Is Recharged Member')
    member_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='Member ID')
    email = models.EmailField(max_length=100, null=True, blank=True, verbose_name='Email')
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name='Address')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_members', verbose_name='Created By')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_members', verbose_name='Updated By')

    class Meta:
        verbose_name = 'Member'
        verbose_name_plural = 'Members'

    def __str__(self):
        return self.name

    @property
    def age(self):
        """Calculate member age"""
        if self.birthday:
            today = timezone.now().date()
            born = self.birthday
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return None


class RechargeRecord(models.Model):
    """Member Recharge Record"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('wechat', 'WeChat'),
        ('alipay', 'Alipay'),
        ('card', 'Bank Card'),
        ('other', 'Other')
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='recharge_records', verbose_name='Member')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Recharge Amount')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Actual Amount')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name='Payment Method')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Operator')
    remark = models.TextField(blank=True, verbose_name='Remarks')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Recharge Time')
    
    class Meta:
        verbose_name = 'Recharge Record'
        verbose_name_plural = 'Recharge Records'
        ordering = ['-created_at']
        
    def __str__(self):
        return f'{self.member.name} - {self.amount}'


class MemberTransaction(models.Model):
    """Member Transaction Record, tracks points and balance changes"""
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('REFUND', 'Refund'),
        ('RECHARGE', 'Recharge'),
        ('POINTS_EARN', 'Points Earned'),
        ('POINTS_REDEEM', 'Points Redeemed'),
        ('POINTS_ADJUST', 'Points Adjustment'),
        ('BALANCE_ADJUST', 'Balance Adjustment'),
        ('LEVEL_UPGRADE', 'Level Upgrade'),
        ('LEVEL_DOWNGRADE', 'Level Downgrade'),
        ('OTHER', 'Other')
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions', verbose_name='Member')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='Transaction Type')
    points_change = models.IntegerField(default=0, verbose_name='Points Change')
    balance_change = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Balance Change')
    description = models.CharField(max_length=255, verbose_name='Description', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Transaction Time')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='member_transactions', verbose_name='Operator')
    related_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='Related Object ID')
    related_object_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='Related Object Type')

    class Meta:
        verbose_name = 'Member Transaction'
        verbose_name_plural = 'Member Transactions'
        ordering = ['-created_at']
        
    def __str__(self):
        change_str = ""
        if self.points_change != 0:
            change_str += f"Points:{self.points_change:+d} "
        if self.balance_change != 0:
            change_str += f"Balance:{self.balance_change:+.2f} "
        return f'{self.member.name} - {self.get_transaction_type_display()} {change_str}' 