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
        
        # Send email notification to store owner
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f'New Contact Form Submission from {name}'
            email_message = f"""
New contact form submission received:

Name: {name}
Email: {email}
Phone: {phone}

Message:
{message}

---
Sent from Gaumaatri Website Contact Form
            """
            
            send_mail(
                subject=subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.STORE_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you soon.")
        except Exception as e:
            print(f"Error sending contact form email: {e}")
            messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you soon.")
        
        # Redirect to the same page to avoid form resubmission
        return redirect('contact')
    
    return render(request, 'store/contact_new.html')

@csrf_exempt
@login_required
def cart(request):
    # Debug: log request details at debug level
    logging.debug(f"Received {request.method} request to cart view from {request.META.get('REMOTE_ADDR')}")
    logging.debug(f"POST data: {dict(request.POST)}")
    logging.debug(f"Headers: {dict(request.headers)}")
    
    # Always get a fresh copy of the cart
    cart = request.session.get('cart', [])
    saved_for_later = request.session.get('saved_for_later', [])
    
    print(f"\n=== CART VIEW START ===")
    print(f"Session ID: {request.session.session_key}")
    print(f"Raw cart from session BEFORE normalization: {cart}")

    # Normalize legacy cart data IMMEDIATELY to ensure consistent comparisons (e.g., size_id as '')
    # This MUST happen before any POST processing so delete operations work correctly
    try:
        normalized = False
        # First pass: normalize fields
        for item in cart:
            if isinstance(item, dict):
                # Ensure product_id is present and stringable
                if 'product_id' in item and item['product_id'] is None:
                    item['product_id'] = ''
                    normalized = True
                # Normalize size_id to '' (empty string) if missing or None
                if item.get('size_id') is None:
                    item['size_id'] = ''
                    normalized = True
                    print(f"  Normalized size_id from None to '' for product {item.get('product_id')}")
                # Ensure quantity is an int >= 1
                try:
                    if 'quantity' in item:
                        q = int(item['quantity'])
                        if q <= 0:
                            item['quantity'] = 1
                            normalized = True
                        else:
                            item['quantity'] = q
                    else:
                        item['quantity'] = 1
                        normalized = True
                except Exception:
                    item['quantity'] = 1
                    normalized = True

        # Second pass: deduplicate by (product_id, size_id)
        combined = {}
        for item in cart:
            if not isinstance(item, dict):
                continue
            pid = str(item.get('product_id', ''))
            sid = str(item.get('size_id') or '')
            if not pid:
                continue
            key = (pid, sid)
            if key not in combined:
                combined[key] = {
                    'product_id': pid,
                    'size_id': sid,
                    'quantity': int(item.get('quantity', 1)),
                    'price': item.get('price')
                }
            else:
                # Merge quantities; prefer existing price
                combined[key]['quantity'] += int(item.get('quantity', 1))
                normalized = True
                print(f"  Merged duplicate entry for product {pid}, size {sid}")

        new_cart_norm = list(combined.values()) if combined else []
        if normalized or (combined and new_cart_norm != cart):
            cart = new_cart_norm
            request.session['cart'] = cart
            request.session.modified = True
            request.session.save()
            print(f"Normalized & saved cart to DB: {cart}")
        else:
            cart = new_cart_norm if combined else cart
            
    except Exception as e:
        print(f"ERROR normalizing cart data: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Cart AFTER normalization: {cart}")
    print(f"=== END CART VIEW START ===\n")
    
    # Debug: Add session tracking
    session_id = request.session.session_key
    logging.debug(f"Cart view - Session ID: {session_id}, Cart: {cart}")
    
    # Early return for empty cart & GET request to optimize performance
    if not cart and not saved_for_later and request.method == 'GET':
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'items': [],
                'subtotal': 0,
                'shipping_cost': 0,
                'total': 0,
                'item_count': 0,
                'cart_count': 0,
            })
        
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
            print(f"\n=== DELETE REQUEST ===")
            print(f"Deleting product ID (POST): {product_id}, size: {size_id}")
            print(f"Session ID before deletion: {request.session.session_key}")
            print(f"Current cart contents BEFORE delete: {cart}")
            print(f"Cart has {len(cart)} items")
            print(f"Cart item types: {[(type(item), item.keys() if isinstance(item, dict) else 'not dict') for item in cart]}")
            
            # Filter out the product-size combination to delete
            cart_before = len(cart)
            print(f"\nFiltering with product_id='{product_id}' (type: {type(product_id)}), size_id='{size_id}' (type: {type(size_id)})")
            
            # Show each comparison
            for idx, item in enumerate(cart):
                pid_match = str(item.get('product_id', '')) == str(product_id)
                sid_match = str(item.get('size_id') or '') == str(size_id or '')
                will_remove = pid_match and sid_match
                print(f"  Item {idx}: pid={repr(item.get('product_id'))}, sid={repr(item.get('size_id'))}")
                print(f"    -> pid_match={pid_match}, sid_match={sid_match}, REMOVE={will_remove}")
            
            new_cart = [item for item in cart if not (
                str(item.get('product_id', '')) == str(product_id) and 
                str(item.get('size_id') or '') == str(size_id or '')
            )]
            
            # Debug: show which items were filtered out
            removed_items = [item for item in cart if (
                str(item.get('product_id', '')) == str(product_id) and 
                str(item.get('size_id') or '') == str(size_id or '')
            )]
            print(f"\nItems that WERE removed: {removed_items}")
            
            cart_after = len(new_cart)
            
            print(f"\nCart before deletion: {cart_before} items, after: {cart_after} items")
            print(f"Items removed: {cart_before - cart_after}")
            print(f"New cart contents: {new_cart}")
            
            # Save the new cart to session and force save for critical operation
            request.session['cart'] = new_cart
            request.session.modified = True
            request.session.save()  # Force save for delete operations to ensure persistence
            
            # Verify the session was actually saved
            print(f"Cart after save: {request.session.get('cart', [])}")
            print(f"Session key after save: {request.session.session_key}")
            print(f"Session modified: {request.session.modified}")
            
            # Check database session
            from django.contrib.sessions.models import Session
            try:
                db_session = Session.objects.get(session_key=request.session.session_key)
                decoded = db_session.get_decoded()
                print(f"Database session cart: {decoded.get('cart', [])}")
            except Session.DoesNotExist:
                print(f"ERROR: Session {request.session.session_key} not found in database!")
            except Exception as e:
                print(f"ERROR checking database session: {e}")
            print(f"=== END DELETE REQUEST ===\n")

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
                                str(item.get('size_id') or '') == str(size_id or '')):
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
                        str(item.get('size_id') or '') == str(size_id or '')):
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
                        str(item.get('size_id') or '') == str(size_id or '')):
                        item['quantity'] += quantity
                        product_exists = True
                        break

                if not product_exists:
                    cart.append({
                        'product_id': product_id, 
                        'quantity': quantity,
                        'size_id': size_id or '',  # Store as empty string if None
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
            
            # ALWAYS load the size object if size_id exists (needed for template display)
            if size_id and str(size_id).isdigit():
                try:
                    selected_size = ProductSize.objects.get(id=int(size_id))
                    # Try to get ProductStock for exact stock
                    try:
                        stock_obj = ProductStock.objects.get(product=product, size_id=size_id)
                        available_stock = stock_obj.quantity
                    except ProductStock.DoesNotExist:
                        available_stock = product.stock_quantity
                except ProductSize.DoesNotExist:
                    pass
            
            # Determine price: prefer the price saved in the cart session
            item_price = item.get('price')
            if item_price is None:
                if size_id:
                    item_price = product.get_price_for_size(int(size_id)) if selected_size else product.discounted_price
                else:
                    item_price = product.discounted_price

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
    
    # Handle AJAX request for cart sidebar
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET':
        try:
            cart_items_data = []
            for item_data in products:
                product = item_data['product']
                size_obj = item_data.get('size')
                size_name = str(size_obj) if size_obj else ''
                
                cart_items_data.append({
                    'id': product.id,
                    'name': product.name,
                    'price': float(item_data['price']),
                    'quantity': item_data['quantity'],
                    'total': float(item_data['item_total']),
                    'image': product.image.url if product.image else None,
                    'size': size_name,
                })
            
            return JsonResponse({
                'success': True,
                'items': cart_items_data,
                'subtotal': float(subtotal),
                'shipping_cost': float(shipping_cost),
                'total': float(total),
                'item_count': item_count,
                'cart_count': item_count,
            })
        except Exception as e:
            logging.error(f"Error creating cart JSON response: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': str(e),
                'items': [],
                'subtotal': 0,
                'shipping_cost': 0,
                'total': 0,
                'item_count': 0,
                'cart_count': 0,
            })
    
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
    
    # Normalize cart data immediately (same as cart view)
    print(f"\n=== CHECKOUT VIEW START ===")
    print(f"Session ID: {request.session.session_key}")
    print(f"Raw cart from session: {cart}")
    
    try:
        normalized = False
        for item in cart:
            if isinstance(item, dict):
                if 'product_id' in item and item['product_id'] is None:
                    item['product_id'] = ''
                    normalized = True
                if item.get('size_id') is None:
                    item['size_id'] = ''
                    normalized = True
                    print(f"  Normalized size_id from None to '' for product {item.get('product_id')}")
                try:
                    if 'quantity' in item:
                        q = int(item['quantity'])
                        item['quantity'] = max(1, q)
                    else:
                        item['quantity'] = 1
                        normalized = True
                except Exception:
                    item['quantity'] = 1
                    normalized = True
        
        if normalized:
            request.session['cart'] = cart
            request.session.modified = True
            request.session.save()
            print(f"Normalized cart in checkout: {cart}")
    except Exception as e:
        print(f"ERROR normalizing cart in checkout: {e}")
    
    print(f"=== END CHECKOUT VIEW START ===\n")
    
    # Get checkout session ID or create a new one
    session_id = request.GET.get('session_id')
    checkout_step = request.GET.get('step', 'address')
    
    # If no checkout ID in URL, generate one and start with address step
    if not session_id:
        session_id = str(uuid.uuid4().hex)
        return redirect(f'/checkout/?session_id={session_id}&step=address')
    
    # Handle delete product request - NOW WITH SIZE SUPPORT
    if request.method == 'POST' and request.POST.get('delete_product'):
        product_id = request.POST.get('delete_product')
        size_id = request.POST.get('size_id', '')  # Get size_id from POST
        
        print(f"\n=== CHECKOUT DELETE REQUEST ===")
        print(f"Deleting product_id={product_id}, size_id={size_id}")
        print(f"Cart before: {cart}")
        
        # Filter out the product-size combination to delete (same logic as cart view)
        new_cart = [item for item in cart if not (
            str(item.get('product_id', '')) == str(product_id) and 
            str(item.get('size_id') or '') == str(size_id or '')
        )]
        
        print(f"Cart after: {new_cart}")
        print(f"Removed {len(cart) - len(new_cart)} items")
        print(f"=== END CHECKOUT DELETE REQUEST ===\n")
        
        request.session['cart'] = new_cart
        request.session.modified = True
        request.session.save()  # Force save
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
    
    # Store payment method and redirect to payment QR or place order
    elif request.method == 'POST' and 'payment_method' in request.POST:
        payment_method = request.POST.get('payment_method', 'cod')
        request.session['payment_method'] = payment_method
        request.session.modified = True
        
        # If UPI payment, show QR code
        if payment_method == 'upi':
            return redirect(f'/checkout/?session_id={session_id}&step=payment-qr')
        else:
            # For COD, proceed to place order directly
            return redirect(f'/checkout/?session_id={session_id}&step=review')
    
    # Process order placement
    elif request.method == 'POST' and request.POST.get('place_order'):
        print(f"Processing order placement with POST data: {request.POST}")
        
        # Get checkout data from session
        checkout_data = request.session.get('checkout_data', {})
        payment_method = request.session.get('payment_method', 'cod')
        payment_verified = request.POST.get('payment_verified', 'false') == 'true'
        
        # For UPI payments, mark as paid if user confirmed
        payment_status = payment_verified if payment_method == 'upi' else False
        
        # Process the form data
        full_name = checkout_data.get('full_name', '')
        email = checkout_data.get('email', '')
        phone = checkout_data.get('phone', '')
        address = checkout_data.get('address', '')
        city = checkout_data.get('city', '')
        state = checkout_data.get('state', '')
        pincode = checkout_data.get('pincode', '')
        
        # Debug data
        print(f"Order data - Name: {full_name}, Email: {email}, Phone: {phone}, Address: {address}")
        print(f"Payment method: {payment_method}, Payment status: {payment_status}")
        
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
                payment_method=payment_method,
                payment_status=payment_status,
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
                
            # Send emails (non-blocking - don't let email failures stop order)
            try:
                process_order_emails(request, order, products)
            except Exception as email_error:
                print(f"Email sending failed but order created: {str(email_error)}")
                # Don't fail the order if email fails
            
            # Clear the cart and checkout data
            request.session['cart'] = []
            request.session.pop('checkout_data', None)
            request.session.pop('payment_method', None)
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
        'step': checkout_step,
        'checkout_data': request.session.get('checkout_data', {}),
        'payment_method': request.session.get('payment_method', 'cod')
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
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('homepage')
        
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
            messages.error(request, "Credentials are incorrect.")
    
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

def terms_conditions(request):
    """Terms & Conditions page view."""
    return render(request, 'store/terms_conditions.html')

def shipping_policy(request):
    """Shipping Policy page view."""
    return render(request, 'store/shipping_policy.html')

def return_policy(request):
    """Return Policy page view."""
    return render(request, 'store/return_policy.html')

def track_order(request):
    """Track Order page view - allows customers to track their orders."""
    order = None
    error_message = None
    
    if request.method == 'POST':
        order_id = request.POST.get('orderId', '').strip()
        email = request.POST.get('email', '').strip()
        
        if order_id:
            try:
                # Try to find the order by order_id (UUID field)
                if email:
                    # If email is provided, verify both order_id and email
                    order = Order.objects.get(order_id=order_id, email=email)
                else:
                    # If only order_id is provided, just check if order exists
                    order = Order.objects.get(order_id=order_id)
            except Order.DoesNotExist:
                if email:
                    error_message = "Order not found. Please check your Order ID and email address."
                else:
                    error_message = "Order not found. Please check your Order ID."
            except Exception as e:
                error_message = "Invalid Order ID format. Please check and try again."
        else:
            error_message = "Please enter an Order ID."
    
    context = {
        'order': order,
        'error_message': error_message,
    }
    
    return render(request, 'store/track_order.html', context)

def customer_service(request):
    """Customer Service page view."""
    return render(request, 'store/customer_service.html')

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
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('homepage')
        
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

def logout_view(request):
    """Custom logout view with proper session cleanup"""
    from django.contrib.auth import logout
    
    # Clear the cart and session data
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        # Optionally clear session data
        request.session.flush()
        messages.success(request, f"Goodbye {username}! You have been logged out successfully.")
    
    return redirect('homepage')

@login_required
def account_view(request):
    """User account/profile page"""
    # Get user's orders
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:10] if request.user.is_authenticated else []
    
    context = {
        'user': request.user,
        'orders': user_orders,
    }
    
    return render(request, 'store/account.html', context)

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
        
        # Send email notification to store owner
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f'New Contact Form Submission from {name}'
            email_message = f"""
New contact form submission received:

Name: {name}
Email: {email}
Phone: {phone}

Message:
{message}

---
Sent from Gaumaatri Website Contact Form
            """
            
            send_mail(
                subject=subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.STORE_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you soon.")
        except Exception as e:
            print(f"Error sending contact form email: {e}")
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
