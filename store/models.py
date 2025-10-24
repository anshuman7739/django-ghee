from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid
import csv
from django.conf import settings
import os
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class ProductSize(models.Model):
    SIZE_CHOICES = (
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('100g', '100 Grams'),
        ('250g', '250 Grams'),
        ('500g', '500 Grams'),
        ('900g', '900 Grams'),
        ('1kg', '1 Kilogram'),
        ('5kg', '5 Kilograms'),
    )
    
    name = models.CharField(max_length=10, choices=SIZE_CHOICES)
    
    def __str__(self):
        return self.get_name_display()
        
class ProductStock(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='size_stocks')
    size = models.ForeignKey(ProductSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=5)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price for this size")
    
    class Meta:
        verbose_name_plural = "Product Stocks"
        unique_together = ('product', 'size')
        
    def __str__(self):
        return f"{self.product.name} - {self.size} ({self.quantity}) - ₹{self.price}"

# Create your models here.
class Product(models.Model):
    FEATURE_CHOICES = (
        ('organic', 'Organic'),
        ('pure_a2', 'Pure A2'),
        ('no_preservatives', 'No Preservatives'),
        ('handmade', 'Handmade'),
        ('gluten_free', 'Gluten Free'),
        ('farm_fresh', 'Farm Fresh'),
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True, help_text="URL-friendly name for product")
    image = models.ImageField(upload_to='products/')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0)
    num_ratings = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=1, help_text="Number of items in stock")
    stock_status = models.CharField(max_length=20, choices=(
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ), default='in_stock')
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True, help_text="Brief product description for listings")
    categories = models.ManyToManyField(Category, related_name='products', blank=True)
    sizes = models.ManyToManyField(ProductSize, related_name='products', blank=True)
    special_features = models.CharField(max_length=100, choices=FEATURE_CHOICES, blank=True, null=True)
    is_featured = models.BooleanField(default=False, help_text="Feature this product on homepage")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    @property
    def discounted_price(self):
        return self.price * (Decimal('1') - Decimal(self.discount_percent) / Decimal('100'))
    
    def get_price_for_size(self, size_id):
        """Get price for a specific size from ProductStock"""
        try:
            stock = self.size_stocks.get(size_id=size_id)
            # Apply discount to stock price
            return stock.price * (Decimal('1') - Decimal(self.discount_percent) / Decimal('100'))
        except ProductStock.DoesNotExist:
            return self.discounted_price
    
    def get_stock_for_size(self, size_id):
        """Get stock quantity for a specific size"""
        try:
            stock = self.size_stocks.get(size_id=size_id)
            return stock.quantity
        except ProductStock.DoesNotExist:
            return self.stock_quantity

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        # Automatically update stock status based on quantity
        # Remove any manual overrides by commenting this condition
        # and always calculate based on the actual quantity
        if self.stock_quantity <= 0:
            self.stock_status = 'out_of_stock'
        elif self.stock_quantity <= 5:
            self.stock_status = 'low_stock'
        else:
            self.stock_status = 'in_stock'
        
        # Generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            # Check if slug already exists
            suffix = 1
            self.slug = base_slug
            while Product.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{suffix}"
                suffix += 1
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(help_text="Discount percentage (0-100)")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fixed discount amount")
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Minimum order amount to apply coupon")
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Maximum discount amount (0 = no limit)")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1, help_text="How many times this coupon can be used")
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.code} - {self.discount_percent}% off"
    
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and 
                self.used_count < self.usage_limit)
    
    def can_apply(self, order_amount):
        return self.is_valid() and order_amount >= self.min_amount
    
    def calculate_discount(self, order_amount):
        if not self.can_apply(order_amount):
            return 0
        
        if self.discount_percent > 0:
            discount = (order_amount * self.discount_percent) / 100
            if self.max_discount > 0:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_amount
            
        return min(discount, order_amount)  # Never exceed order amount
        
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHODS = (
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('upi', 'UPI Transfer'),
    )
    
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cod')
    payment_status = models.BooleanField(default=False, verbose_name="Payment Received")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about this order")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_id} - {self.full_name}"
        
    @classmethod
    def export_to_csv(cls):
        """Export all orders to a CSV file"""
        csv_file_path = os.path.join(settings.BASE_DIR, 'order_export.csv')
        
        orders = cls.objects.all().prefetch_related('items', 'items__product')
        
        with open(csv_file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Order ID', 'Date', 'Customer', 'Email', 'Phone', 
                            'Address', 'City', 'State', 'Pincode',
                            'Items', 'Total Amount', 'Payment Method', 'Payment Status', 'Order Status'])
            
            # Write data
            for order in orders:
                items_str = '; '.join([f"{item.quantity}x {item.product.name}" for item in order.items.all()])
                
                writer.writerow([
                    str(order.order_id),
                    order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    order.full_name,
                    order.email,
                    order.phone,
                    order.address.replace('\n', ' '),
                    order.city,
                    order.state,
                    order.pincode,
                    items_str,
                    order.total_amount,
                    order.get_payment_method_display(),
                    'Paid' if order.payment_status else 'Unpaid',
                    order.get_status_display(),
                ])
        
        return csv_file_path
        
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.order.order_id}"
    
    @property
    def total_price(self):
        if self.price is None:
            return 0
        return self.price * self.quantity
