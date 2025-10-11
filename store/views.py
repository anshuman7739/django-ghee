from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .email_utils import send_order_confirmation_emails
from .models import Product, Order, OrderItem, Category, ProductSize, ProductStock, Coupon
from django.db.models import Q
from .utils import track_recently_viewed
import uuid
from django.core.paginator import Paginator
import json
import logging

# Create your views here.

def simple_cart(request):
    """
    A simplified cart view to troubleshoot issues
    """
    # Always get a fresh copy of the cart
    cart = request.session.get('cart', [])
    
    # For AJAX requests
    if request.method == 'POST' and request.POST.get('update_cart') and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Handle quantity update for a single product
        single_product_id = request.POST.get('single_product_id')
        if single_product_id:
            qty_key = f"quantity_{single_product_id}"
            if qty_key in request.POST:
                try:
                    new_qty = int(request.POST.get(qty_key))
                    if new_qty > 0:
                        # Update the quantity in the cart
                        for item in cart:
                            if str(item.get('product_id', '')) == str(single_product_id):
                                item['quantity'] = new_qty
                                break
                        
                        request.session['cart'] = cart
                        request.session.modified = True
                        
                        # Calculate cart totals
                        subtotal = 0
                        for item in cart:
                            product_id = item.get('product_id')
                            size_id = item.get('size_id')
                            if product_id and str(product_id).isdigit():
                                try:
                                    product = Product.objects.get(id=int(product_id))
                                    # Prefer stored cart item price if present (stored at add-to-cart time)
                                    price = item.get('price')
                                    if price is None:
                                        if size_id:
                                            price = product.get_price_for_size(int(size_id))
                                        else:
                                            price = product.discounted_price
                                    subtotal += float(price) * item['quantity']
                                except Exception:
                                    logging.exception("Error calculating item price in simple_cart")
                        
                        shipping_threshold = 1000
                        shipping_cost = 0 if subtotal >= shipping_threshold else 50
                        total = subtotal + shipping_cost
                        
                        return JsonResponse({
                            'success': True,
                            'subtotal': round(subtotal, 2),
                            'shipping_cost': shipping_cost,
                            'total': round(total, 2)
                        })
                except (ValueError, TypeError) as e:
                    logging.exception("Error processing quantity update")
    
    # Normal page display
    products = []
    subtotal = 0
    
    # Get all cart items with product data
    for item in cart:
        try:
            product_id = item.get('product_id')
            size_id = item.get('size_id')
            if not product_id or not str(product_id).isdigit():
                continue
                
            product = Product.objects.get(id=int(product_id))
            quantity = item['quantity']
            
            # Use size-specific pricing if size_id is available
            if size_id:
                item_price = product.get_price_for_size(int(size_id))
            else:
                item_price = product.discounted_price
                
            item_total = item_price * quantity
            
            products.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total,
                'size_id': size_id,
                'price': item_price
            })
            
            subtotal += item_total
        except Exception:
            logging.exception("Error processing cart item in simple_cart")
    
    shipping_threshold = 1000
    shipping_cost = 0 if subtotal >= shipping_threshold else 50
    total = subtotal + shipping_cost
    
    return render(request, 'store/simple_cart.html', {
        'cart_items': products,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    })

def homepage(request):
    fallback_image = request.build_absolute_uri('/static/store/images/banner1.jpg')
    return render(request, 'store/homepage_clean.html', {'fallback_image': fallback_image})

def homepage_old(request):
    fallback_image = request.build_absolute_uri('/static/store/images/banner1.jpg')
    return render(request, 'store/homepage_new.html', {'fallback_image': fallback_image})

def shop(request):
    # Get all products with related data
    products = Product.objects.all().prefetch_related('sizes', 'size_stocks').order_by('-created_at')
    
    # Import Decimal for proper calculations
    from decimal import Decimal
    
    # Create a mapping of product sizes to their prices and stock
    product_size_data = {}
    initial_prices = {}
    for product in products:
        product_size_data[product.id] = {}
        # Get the first size for initial price
        first_stock = product.size_stocks.first()
        if first_stock:
            discount_multiplier = Decimal('1') - Decimal(product.discount_percent) / Decimal('100')
            initial_discounted_price = first_stock.price * discount_multiplier
            initial_prices[product.id] = float(initial_discounted_price)
        
        for stock in product.size_stocks.all():
            discount_multiplier = Decimal('1') - Decimal(product.discount_percent) / Decimal('100')
            discounted_price = stock.price * discount_multiplier
            product_size_data[product.id][stock.size.id] = {
                'price': float(discounted_price),
                'original_price': float(stock.price),
                'stock': stock.quantity
            }
    
    context = {
        'products': products,
        'product_size_data': json.dumps(product_size_data),
        'initial_prices': initial_prices,
    'cart_count': sum(item.get('quantity', 0) for item in request.session.get('cart', [])),
    }
    
    return render(request, 'store/shop_new.html', context)

def contact(request):
    """Updated contact page view using the new template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save the contact form data
        # For now, we'll just add a success message
        messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you soon.")
        
        # Redirect to the same page to avoid form resubmission
        return redirect('contact')
    
    return render(request, 'store/contact_new.html')

@csrf_exempt
@login_required
def cart(request):
    # Debug: log request details at debug level
    logging.debug(f"Received {request.method} request to cart view from {request.META.get('REMOTE_ADDR')}")
    
    # Always get a fresh copy of the cart
    cart = request.session.get('cart', [])
    saved_for_later = request.session.get('saved_for_later', [])
    
    # Early return for empty cart & GET request to optimize performance
    if not cart and not saved_for_later and request.method == 'GET':
        return render(request, 'store/cart.html', {
            'cart_items': [],
            'saved_items': [],
            'subtotal': 0,
            'shipping_cost': 0,
            'shipping_threshold': 1000,  # Default shipping threshold
            'gift_wrap': False,
            'gift_wrap_cost': 50,
            'total': 0,
            'item_count': 0,
            'suggested_products': [],
            'recently_viewed_products': []
        })
    
    logging.debug(f"Initial cart: {cart}")
    logging.debug(f"Saved for later: {saved_for_later}")
    
    # Handle delete via GET (from our link)
    if request.method == 'GET' and request.GET.get('delete_product'):
        product_id = request.GET.get('delete_product')
        # Remove item and mark session modified; avoid forcing immediate session.save() which can be slow
        new_cart = [item for item in cart if str(item.get('product_id', '')) != str(product_id)]
        request.session['cart'] = new_cart
        request.session.modified = True
        return redirect('cart')
    
    if request.method == 'POST':
        # Delete product from cart
        if request.POST.get('delete_product'):
            product_id = request.POST.get('delete_product')
            size_id = request.POST.get('size_id')
            logging.debug(f"Deleting product ID (POST): {product_id}, size: {size_id}")
            logging.debug(f"Current cart contents: {cart}")
            
            # Filter out the product-size combination to delete
            cart_before = len(cart)
            new_cart = [item for item in cart if not (
                str(item.get('product_id', '')) == str(product_id) and 
                str(item.get('size_id', '')) == str(size_id or '')
            )]
            cart_after = len(new_cart)
            
            logging.debug(f"Cart before deletion: {cart_before} items, after: {cart_after} items")
            logging.debug(f"Items removed: {cart_before - cart_after}")
            
            # Save the new cart to session and force save for critical operation
            request.session['cart'] = new_cart
            request.session.modified = True
            request.session.save()  # Force save for delete operations to ensure persistence
            
            # Verify the session was actually saved
            logging.debug(f"Cart after save: {request.session.get('cart', [])}")
            logging.debug(f"Session key: {request.session.session_key}")
            logging.debug(f"Session modified: {request.session.modified}")

            # Return minimal JSON for AJAX delete (fast response, no DB queries)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                total_items = sum(item.get('quantity', 0) for item in new_cart)
                return JsonResponse({
                    'success': True, 
                    'cart_count': total_items
                })
                
            return redirect('cart')
        
        # Update quantities - optimized for speed
        elif request.POST.get('update_cart'):
            # Check if we're updating a single product (AJAX update) or the whole cart
            single_product_id = request.POST.get('single_product_id')
            
            if single_product_id:
                # Fast path: only update one product quantity
                size_id = request.POST.get('size_id')
                qty_key = f"quantity_{single_product_id}"
                if qty_key in request.POST:
                    new_qty = int(request.POST.get(qty_key))
                    if new_qty > 0:
                        # Find and update just this one product-size combination
                        for item in cart:
                            if (str(item.get('product_id', '')) == str(single_product_id) and 
                                str(item.get('size_id', '')) == str(size_id or '')):
                                item['quantity'] = new_qty
                                break
            else:
                # Standard path: update all quantities
                new_cart = []
                for item in cart:
                    qty_key = f"quantity_{item['product_id']}"
                    if qty_key in request.POST:
                        new_qty = int(request.POST.get(qty_key))
                        if new_qty > 0:
                            item['quantity'] = new_qty
                            new_cart.append(item)
                    else:
                        # Keep the item with its original quantity if no update
                        new_cart.append(item)
                
                cart = new_cart
            
            request.session['cart'] = cart
            request.session.modified = True  # Force session save
            
            # Return JSON response if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Skip heavy DB queries and calculations - let client update totals from DOM
                total_items = sum(item.get('quantity', 0) for item in cart)
                return JsonResponse({
                    'success': True,
                    'cart_count': total_items
                })
            return redirect('cart')
        
        # Update gift wrap option
        elif request.POST.get('update_gift_wrap') is not None:
            gift_wrap = 'gift_wrap' in request.POST
            request.session['gift_wrap'] = gift_wrap
            request.session.modified = True
            logging.debug(f"Updated gift wrap option to: {gift_wrap}")
            return redirect('cart')
            
        # Save item for later
        elif request.POST.get('save_for_later'):
            product_id = request.POST.get('save_for_later')
            logging.debug(f"Saving product ID {product_id} for later")
            
            # Find the item in the cart
            saved_item = None
            for item in cart:
                if str(item.get('product_id', '')) == str(product_id):
                    saved_item = item
                    break
            
            if saved_item:
                # Remove from cart
                cart = [item for item in cart if str(item.get('product_id', '')) != str(product_id)]
                
                # Add to saved for later list
                saved_for_later.append(saved_item)
                
                # Update session
                request.session['cart'] = cart
                request.session['saved_for_later'] = saved_for_later
                request.session.modified = True
            
            return redirect('cart')
            
        # Move item to cart
        elif request.POST.get('move_to_cart'):
            product_id = request.POST.get('move_to_cart')
            logging.debug(f"Moving product ID {product_id} to cart")
            
            # Find the item in saved for later
            item_to_move = None
            for item in saved_for_later:
                if str(item.get('product_id', '')) == str(product_id):
                    item_to_move = item
                    break
            
            if item_to_move:
                # Remove from saved for later
                saved_for_later = [item for item in saved_for_later if str(item.get('product_id', '')) != str(product_id)]
                
                # Add to cart
                cart.append(item_to_move)
                
                # Update session
                request.session['cart'] = cart
                request.session['saved_for_later'] = saved_for_later
                request.session.modified = True
            
            return redirect('cart')
        
        # Apply coupon code
        elif request.POST.get('coupon_code'):
            coupon_code = request.POST.get('coupon_code').strip().upper()
            
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                
                # Calculate current cart total
                cart_total = 0
                for item in cart:
                    try:
                        product = Product.objects.get(id=item['product_id'])
                        size_id = item.get('size_id')
                        if size_id:
                            price = product.get_price_for_size(int(size_id))
                        else:
                            price = product.discounted_price
                        cart_total += price * item['quantity']
                    except Product.DoesNotExist:
                        continue
                
                if coupon.can_apply(cart_total):
                    discount = coupon.calculate_discount(cart_total)
                    request.session['applied_coupon'] = {
                        'code': coupon.code,
                        'discount': float(discount)
                    }
                    request.session.modified = True
                    messages.success(request, f"Coupon '{coupon.code}' applied! You saved ₹{discount:.2f}")
                else:
                    if not coupon.is_valid():
                        messages.error(request, "This coupon has expired or is no longer valid.")
                    else:
                        messages.error(request, f"Minimum order amount of ₹{coupon.min_amount} required for this coupon.")
                        
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code.")
            
            return redirect('cart')
        
        # Remove coupon
        elif request.POST.get('remove_coupon'):
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
                request.session.modified = True
                messages.success(request, "Coupon removed.")
            return redirect('cart')
            
        # Add new product to cart
        elif request.POST.get('product_id'):
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            size_id = request.POST.get('size_id')
            
            # Check stock availability
            try:
                product = Product.objects.get(id=product_id)
                
                # If size is specified, check ProductStock, otherwise use general stock
                if size_id:
                    try:
                        product_stock = ProductStock.objects.get(product=product, size_id=size_id)
                        available_stock = product_stock.quantity
                    except ProductStock.DoesNotExist:
                        messages.error(request, "Sorry, this product size is not available.")
                        if request.META.get('HTTP_REFERER'):
                            return redirect(request.META.get('HTTP_REFERER'))
                        return redirect('product_detail', product_id=product_id)
                else:
                    available_stock = product.stock_quantity
                
                # Calculate current quantity in cart for this product-size combination
                current_in_cart = 0
                for item in cart:
                    if (str(item.get('product_id', '')) == str(product_id) and 
                        str(item.get('size_id', '')) == str(size_id or '')):
                        current_in_cart = item['quantity']
                        break
                
                # Check if requested quantity exceeds stock
                if current_in_cart + quantity > available_stock:
                    messages.error(request, f"Sorry, only {available_stock} item(s) available for this size. You already have {current_in_cart} in your cart.")
                    if request.META.get('HTTP_REFERER'):
                        return redirect(request.META.get('HTTP_REFERER'))
                    return redirect('product_detail', product_id=product_id)

                # Determine price for this size (store with cart item for consistency)
                if size_id:
                    try:
                        item_price = float(product.get_price_for_size(int(size_id)))
                    except Exception:
                        item_price = float(product.discounted_price)
                else:
                    item_price = float(product.discounted_price)

                # Check if product-size combination already exists in cart
                product_exists = False
                for item in cart:
                    if (str(item.get('product_id', '')) == str(product_id) and 
                        str(item.get('size_id', '')) == str(size_id or '')):
                        item['quantity'] += quantity
                        product_exists = True
                        break

                if not product_exists:
                    cart.append({
                        'product_id': product_id, 
                        'quantity': quantity,
                        'size_id': size_id,
                        'price': item_price
                    })
                
                request.session['cart'] = cart
                request.session.modified = True  # Force session save
                logging.debug(f"Added product {product_id} (size: {size_id}) to cart, new cart: {cart}")
                
                # Return JSON for AJAX cart adds
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Calculate total items in cart for the badge
                    total_items = sum(item.get('quantity', 0) for item in cart)
                    return JsonResponse({
                        'success': True,
                        'message': f"Added {quantity} {product.name} to your cart.",
                        'cart_count': total_items,
                        'product_name': product.name,
                        'product_image': product.image.url if product.image else None,
                    })
                
            except Product.DoesNotExist:
                messages.error(request, "Sorry, this product is not available.")
                
            if request.META.get('HTTP_REFERER'):
                return redirect(request.META.get('HTTP_REFERER'))
            return redirect('cart')
    
    # Clean up cart by removing None product_ids
    cleaned_cart = [item for item in cart if item.get('product_id') is not None]
    if len(cleaned_cart) != len(cart):
        cart = cleaned_cart
        request.session['cart'] = cart
        request.session.modified = True
        logging.debug(f"Cleaned cart: {cart}")
        
    # Process cart items for display - optimized for speed
    import time
    start_time = time.time()
    
    products = []
    saved_products = []
    from decimal import Decimal
    
    subtotal = Decimal('0')
    item_count = 0
    
    # Constants
    SHIPPING_THRESHOLD = 1000  # Free shipping for orders above this amount
    SHIPPING_COST = 50
    GIFT_WRAP_COST = 50
    
    # Clean up cart in one pass - faster than creating new lists
    valid_product_ids = set()
    i = 0
    while i < len(cart):
        item = cart[i]
        if not item.get('product_id') or not str(item.get('product_id')).isdigit():
            cart.pop(i)
            request.session.modified = True
        else:
            valid_product_ids.add(int(item['product_id']))
            i += 1
    
    # Get all products in one optimized query 
    product_map = {}
    if valid_product_ids:
        # Get all products - don't use only() as it breaks property access
        products_query_time = time.time()
        for product in Product.objects.filter(id__in=valid_product_ids):
            product_map[product.id] = product
        logging.debug(f"Product query took {(time.time() - products_query_time)*1000:.2f}ms")
    
    for item in cart:
        try:
            product_id = item.get('product_id')
            if not product_id or not str(product_id).isdigit():
                continue
                
            product_id = int(product_id)
            product = product_map.get(product_id)
            if not product:
                continue
                
            quantity = item['quantity']
            size_id = item.get('size_id')
            
            # Get size information and determine price (prefer stored cart item price)
            selected_size = None
            available_stock = product.stock_quantity
            # Determine price: prefer the price saved in the cart session
            item_price = item.get('price')
            if item_price is None:
                if size_id:
                    try:
                        selected_size = ProductSize.objects.get(id=size_id)
                        # Try to get ProductStock for exact stock
                        try:
                            stock_obj = ProductStock.objects.get(product=product, size_id=size_id)
                            available_stock = stock_obj.quantity
                        except ProductStock.DoesNotExist:
                            available_stock = product.stock_quantity
                        item_price = product.get_price_for_size(int(size_id))
                    except ProductSize.DoesNotExist:
                        item_price = product.discounted_price
                        available_stock = product.stock_quantity
                else:
                    item_price = product.discounted_price
                    available_stock = product.stock_quantity

            item_total = Decimal(str(item_price)) * quantity

            products.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total,
                'size': selected_size,
                'price': float(item_price),
                'available_stock': available_stock
            })
            
            subtotal += item_total
            item_count += quantity
        except Product.DoesNotExist:
            logging.debug(f"Product with ID {item['product_id']} not found")
            continue
        except Exception:
            logging.exception("Error processing cart item in main loop")
            continue
    
    # Clean up saved_for_later by removing None product_ids
    cleaned_saved = [item for item in saved_for_later if item.get('product_id') is not None]
    if len(cleaned_saved) != len(saved_for_later):
        saved_for_later = cleaned_saved
        request.session['saved_for_later'] = saved_for_later
        request.session.modified = True
    
    # Get saved for later product IDs
    saved_product_valid_ids = []
    for item in saved_for_later:
        try:
            product_id = item.get('product_id')
            if product_id and str(product_id).isdigit():
                saved_product_valid_ids.append(int(product_id))
        except (ValueError, TypeError):
            continue
            
    # Batch fetch saved products
    saved_product_map = {}
    if saved_product_valid_ids:
        for product in Product.objects.filter(id__in=saved_product_valid_ids):
            saved_product_map[product.id] = product
    
    # Process saved for later items
    for item in saved_for_later:
        try:
            product_id = item.get('product_id')
            if not product_id or not str(product_id).isdigit():
                continue
                
            product_id = int(product_id)
            product = saved_product_map.get(product_id)
            if not product:
                continue
                
            quantity = item['quantity']
            
            saved_products.append({
                'product': product,
                'quantity': quantity
            })
        except (Product.DoesNotExist, ValueError, TypeError):
            continue
        except Exception:
            logging.exception("Error processing saved item")
            continue
    
    # Calculate shipping cost
    shipping_cost = Decimal('0') if subtotal >= SHIPPING_THRESHOLD else Decimal(str(SHIPPING_COST))
    
    # Apply coupon discount
    coupon_discount = Decimal('0')
    applied_coupon = request.session.get('applied_coupon')
    if applied_coupon:
        coupon_discount = Decimal(str(applied_coupon.get('discount', 0)))
    
    # Calculate total
    total = subtotal - coupon_discount + shipping_cost
    
    # Get gift wrap status from session
    gift_wrap = request.session.get('gift_wrap', False)
    if gift_wrap:
        total += Decimal(str(GIFT_WRAP_COST))
    
    # Skip suggested and recently viewed products if cart is empty to speed up load time
    suggested_products = []
    recently_viewed_products = []
    
    if products:  # Only load these if cart has items
        # Get suggested products (excluding ones already in cart and saved for later) - limited to 4
        cart_product_ids = [int(item['product_id']) for item in cart if item['product_id'] and item['product_id'].isdigit()]
        saved_product_ids = [int(item['product_id']) for item in saved_for_later if item['product_id'] and item['product_id'].isdigit()]
        excluded_ids = cart_product_ids + saved_product_ids
        
        # Use select_related to reduce database queries
        suggested_products = list(Product.objects.exclude(id__in=excluded_ids).order_by('?')[:4])
        
        # Get recently viewed products from session - limited to 4
        recently_viewed = request.session.get('recently_viewed', [])[:4]
        if recently_viewed:
            recently_viewed_products = list(Product.objects.filter(id__in=recently_viewed))
            # Sort them according to the order in the session
            recently_viewed_products.sort(key=lambda x: recently_viewed.index(x.id))
    
    return render(request, 'store/cart.html', {
        'cart_items': products,
        'saved_items': saved_products,
        'subtotal': subtotal,
        'coupon_discount': coupon_discount,
        'shipping_cost': shipping_cost,
        'shipping_threshold': SHIPPING_THRESHOLD,
        'gift_wrap': gift_wrap,
        'gift_wrap_cost': GIFT_WRAP_COST,
        'total': total,
        'item_count': item_count,
        'suggested_products': suggested_products,
        'recently_viewed_products': recently_viewed_products
    })

import uuid
import time

def checkout(request):
    cart = request.session.get('cart', [])
    print(f"Checkout cart contents: {cart}")
    
    # Get checkout session ID or create a new one
    session_id = request.GET.get('session_id')
    checkout_step = request.GET.get('step', 'address')
    
    # If no checkout ID in URL, generate one and start with address step
    if not session_id:
        session_id = str(uuid.uuid4().hex)
        return redirect(f'/checkout/?session_id={session_id}&step=address')
    
    # Handle delete product request
    if request.method == 'POST' and request.POST.get('delete_product'):
        product_id = request.POST.get('delete_product')
        # Filter out the product to delete
        new_cart = [item for item in cart if str(item.get('product_id', '')) != str(product_id)]
        request.session['cart'] = new_cart
        request.session.modified = True
        return redirect(f'/checkout/?session_id={session_id}&step={checkout_step}')
    
    # Update quantities
    elif request.method == 'POST' and request.POST.get('update_cart'):
        print(f"Updating cart quantities from checkout. Current cart: {cart}")
        new_cart = []
        for item in cart:
            qty_key = f"quantity_{item['product_id']}"
            if qty_key in request.POST:
                new_qty = int(request.POST.get(qty_key))
                print(f"Updating product {item['product_id']} quantity to {new_qty}")
                if new_qty > 0:
                    item['quantity'] = new_qty
                    new_cart.append(item)
            else:
                # Keep the item with its original quantity if no update
                new_cart.append(item)
                
        request.session['cart'] = new_cart
        request.session.modified = True  # Force session save
        print(f"Updated cart: {new_cart}")
        return redirect(f'/checkout/?session_id={session_id}&step={checkout_step}')
    
    # Store address information
    elif request.method == 'POST' and 'first_name' in request.POST and 'last_name' in request.POST:
        # Store shipping details in session for later use
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        checkout_data = {
            'full_name': f"{first_name} {last_name}".strip(),
            'email': request.POST.get('email', ''),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
            'city': request.POST.get('city', ''),
            'state': request.POST.get('state', ''),
            'pincode': request.POST.get('zipcode', ''),
            'order_notes': request.POST.get('order_notes', '')
        }
        
        request.session['checkout_data'] = checkout_data
        request.session.modified = True
        
        # Redirect to payment step
        return redirect(f'/checkout/?session_id={session_id}&step=payment')
    
    # Process order placement
    elif request.method == 'POST' and request.POST.get('place_order'):
        print(f"Processing order placement with POST data: {request.POST}")
        # Process the form data
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        
        # Debug data
        print(f"Order data - Name: {full_name}, Email: {email}, Phone: {phone}, Address: {address}")
        
        # Process cart items
        products = []
        total = 0
        for item in cart:
            try:
                product = Product.objects.get(id=item['product_id'])
                size_id = item.get('size_id')
                
                # Use size-specific pricing
                if size_id:
                    item_price = product.get_price_for_size(int(size_id))
                else:
                    item_price = product.discounted_price
                    
                item_total = item_price * item['quantity']
                products.append({
                    'product': product, 
                    'quantity': item['quantity'],
                    'total': item_total,
                    'size_id': size_id
                })
                total += item_total
            except Product.DoesNotExist:
                print(f"Product with ID {item['product_id']} not found")
                continue
            except Exception as e:
                print(f"Error processing checkout item: {str(e)}")
                continue
                
        # Create an order in the database
        try:
            # Create the order
            order = Order.objects.create(
                order_id=uuid.uuid4(),
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                total_amount=total,
                status='pending'
            )
            
            # Create order items
            for item in products:
                size_id = item.get('size_id')
                if size_id:
                    item_price = item['product'].get_price_for_size(int(size_id))
                else:
                    item_price = item['product'].discounted_price
                    
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item_price
                )
                
            # Send emails
            process_order_emails(request, order, products)
            
            # Clear the cart
            request.session['cart'] = []
            request.session.modified = True
            
            messages.success(request, "Order placed successfully! Confirmation email sent.")
            return redirect('order_confirmation', order_id=order.order_id)
            
        except Exception as e:
            import traceback
            print(f"Error creating order: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, "There was an error processing your order. Please try again.")
            
    # Process cart items for display
    products = []
    subtotal = 0
    for item in cart:
        try:
            product = Product.objects.get(id=item['product_id'])
            size_id = item.get('size_id')
            
            # Use size-specific pricing
            if size_id:
                item_price = product.get_price_for_size(int(size_id))
            else:
                item_price = product.discounted_price
                
            item_total = item_price * item['quantity']
            products.append({
                'product': product, 
                'quantity': item['quantity'],
                'total': item_total,
                'size_id': size_id
            })
            subtotal += item_total
        except Product.DoesNotExist:
            print(f"Product with ID {item['product_id']} not found")
            continue
        except Exception as e:
            print(f"Error processing checkout item: {str(e)}")
            continue
    
    # Calculate shipping cost
    SHIPPING_THRESHOLD = 1000
    SHIPPING_COST = 50
    shipping_cost = 0 if subtotal >= SHIPPING_THRESHOLD else SHIPPING_COST
    
    # Apply coupon discount
    coupon_discount = 0
    applied_coupon = request.session.get('applied_coupon')
    if applied_coupon:
        from decimal import Decimal
        coupon_discount = Decimal(str(applied_coupon.get('discount', 0)))
    
    # Calculate total
    total = subtotal - coupon_discount + shipping_cost
    
    # Get gift wrap status
    gift_wrap = request.session.get('gift_wrap', False)
    GIFT_WRAP_COST = 50
    if gift_wrap:
        total += GIFT_WRAP_COST
    
    # If cart is empty, redirect to cart page
    if not products:
        messages.warning(request, "Your cart is empty. Please add items before proceeding to checkout.")
        return redirect('cart')
    
    context = {
        'cart_items': products,
        'subtotal': subtotal,
        'coupon_discount': coupon_discount,
        'shipping_cost': shipping_cost,
        'shipping_threshold': SHIPPING_THRESHOLD,
        'gift_wrap': gift_wrap,
        'gift_wrap_cost': GIFT_WRAP_COST if gift_wrap else 0,
        'total': total,
        'session_id': session_id,
        'step': checkout_step
    }
    
    return render(request, 'store/checkout_premium.html', context)
    
def process_order_emails(request, order, products):
    """Send order confirmation emails to both customer and store owner"""
    
    # Get site URL for email templates
    site_url = request.build_absolute_uri('/')[:-1]  # Get base URL without trailing slash
    
    # Send confirmation emails to both customer and store owner using the utility function
    from .email_utils import send_order_confirmation_emails
    customer_sent, owner_sent = send_order_confirmation_emails(
        order=order,
        products=products,
        site_url=site_url
    )
    
    # Log the result
    if customer_sent and owner_sent:
        print(f"Order confirmation emails sent for order #{order.order_id}")
    else:
        print(f"Some order confirmation emails failed for order #{order.order_id}")
        
def order_confirmation(request, order_id):
    """View to display order confirmation page"""
    try:
        order = Order.objects.get(order_id=order_id)
        order_items = order.items.all()
        
        return render(request, 'store/order_confirmation.html', {
            'order': order,
            'order_items': order_items
        })
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('homepage')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', '')
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if next_url and next_url != '/':
                return redirect(next_url)
            else:
                return redirect('homepage')
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'store/login.html')

def search_products(request):
    query = request.GET.get('q', '')
    products = []
    
    if query:
        # Search in product name and description
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    fallback_image = request.build_absolute_uri('/static/store/images/banner1.jpg')
    return render(request, 'store/search_results.html', {
        'products': products,
        'query': query,
        'fallback_image': fallback_image
    })

def benefits(request):
    fallback_image = request.build_absolute_uri('/static/store/images/banner1.jpg')
    return render(request, 'store/benefits.html', {'fallback_image': fallback_image})
    
def privacy_policy(request):
    """Privacy Policy page view."""
    return render(request, 'store/privacy_policy.html')

def product_detail(request, product_id):
    """Product detail view.
    
    This view shows the details of a product and tracks it in the recently viewed products list.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Track this product in recently viewed list
    track_recently_viewed(request, product_id)
    
    # Get related products (excluding the current one)
    related_products = Product.objects.exclude(id=product_id).order_by('?')[:4]
    
    fallback_image = request.build_absolute_uri('/static/store/images/banner1.jpg')
    
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'fallback_image': fallback_image
    })

def register_view(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            password1 = request.POST['password1']
            password2 = request.POST['password2']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            
            # Check if passwords match
            if password1 != password2:
                messages.error(request, "Passwords don't match")
                return render(request, 'store/register.html')
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return render(request, 'store/register.html')
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already in use")
                return render(request, 'store/register.html')
            
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # Log the user in
            login(request, user)
            messages.success(request, "Registration successful! Welcome to Pure Desi Ghee.")
            return redirect('homepage')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return render(request, 'store/register.html')

def about(request):
    """About us page view"""
    return render(request, 'store/about.html')

def contact_new(request):
    """New contact page view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save the contact form data
        # For now, we'll just add a success message
        messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you soon.")
        
        # Redirect to the same page to avoid form resubmission
        return redirect('contact_new')
    
    return render(request, 'store/contact_new.html')

def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Here you would typically save the email to your newsletter database
            # For now, we'll just show a success message
            messages.success(request, "Thank you for subscribing to our newsletter!")
        else:
            messages.error(request, "Please enter a valid email address.")
    
    return redirect('homepage')
