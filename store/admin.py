from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Product, Order, OrderItem, Category, ProductSize, ProductStock, Coupon

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'product_count')
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_image', 'price', 'get_discounted_price', 'discount_percent', 
                   'stock_status', 'stock_quantity', 'display_categories', 'display_sizes', 
                   'special_features', 'is_featured')
    list_filter = ('stock_status', 'is_featured', 'categories', 'special_features', 'sizes')
    search_fields = ('name', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('categories', 'sizes')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_featured', 'discount_percent', 'stock_quantity')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'image', 'price', 'discount_percent', 'stock_quantity',
                       'stock_status', 'is_featured')
        }),
        ('Descriptions', {
            'fields': ('short_description', 'description'),
            'classes': ('collapse',),
        }),
        ('Categorization', {
            'fields': ('categories', 'sizes', 'special_features'),
        }),
        ('Metrics', {
            'fields': ('rating', 'num_ratings', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('stock_status', 'created_at', 'updated_at')
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Image'
    
    def display_categories(self, obj):
        return ", ".join([cat.name for cat in obj.categories.all()])
    display_categories.short_description = 'Categories'
    
    def display_sizes(self, obj):
        return ", ".join([str(size) for size in obj.sizes.all()])
    display_sizes.short_description = 'Sizes'
    
    def get_discounted_price(self, obj):
        return obj.discounted_price
    get_discounted_price.short_description = 'Discounted Price'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'total_price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'full_name', 'email', 'total_amount', 'payment_status',
                    'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'full_name', 'email', 'phone', 'tracking_number')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['export_orders_to_csv', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'full_name', 'email', 'phone')
        }),
        ('Shipping Details', {
            'fields': ('address', 'city', 'state', 'pincode', 'tracking_number')
        }),
        ('Order Details', {
            'fields': ('order_id', 'total_amount', 'payment_method', 'payment_status', 
                       'status', 'notes', 'created_at', 'updated_at')
        }),
    )
    
    def export_orders_to_csv(self, request, queryset):
        # Export selected orders to CSV
        csv_file_path = Order.export_to_csv()
        self.message_user(request, f"Orders exported successfully to {csv_file_path}")
    export_orders_to_csv.short_description = "Export selected orders to CSV"
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f"{queryset.count()} orders marked as processing")
    mark_as_processing.short_description = "Mark selected orders as processing"
    
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f"{queryset.count()} orders marked as shipped")
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f"{queryset.count()} orders marked as delivered")
    mark_as_delivered.short_description = "Mark selected orders as delivered"
    
@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'quantity')
    list_filter = ('product', 'size')
    search_fields = ('product__name',)
    
    class Media:
        js = ('admin/js/stock_admin.js',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'discount_amount', 'min_amount', 'max_discount', 
                   'valid_from', 'valid_to', 'usage_limit', 'used_count', 'is_active', 'is_valid_now')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    list_editable = ('is_active',)
    readonly_fields = ('used_count',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'is_active')
        }),
        ('Discount Details', {
            'fields': ('discount_percent', 'discount_amount', 'min_amount', 'max_discount'),
            'description': 'Use either discount_percent OR discount_amount, not both.'
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'usage_limit', 'used_count')
        }),
    )
    
    def is_valid_now(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_now.short_description = 'Current Status'
    
    def save_model(self, request, obj, form, change):
        # Ensure only one discount type is used
        if obj.discount_percent > 0:
            obj.discount_amount = 0
        elif obj.discount_amount > 0:
            obj.discount_percent = 0
        super().save_model(request, obj, form, change)
