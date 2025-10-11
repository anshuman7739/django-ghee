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
                        from .models import Product
                        import time
                        
                        start_time = time.time()
                        print(f"Processing AJAX cart update for {single_product_id}")
                        
                        subtotal = 0
                        for item in cart:
                            product_id = item.get('product_id')
                            if product_id and str(product_id).isdigit():
                                try:
                                    product = Product.objects.get(id=int(product_id))
                                    subtotal += float(product.discounted_price) * item['quantity']
                                except Exception as e:
                                    print(f"Error calculating item price: {e}")
                        
                        shipping_threshold = 1000
                        shipping_cost = 0 if subtotal >= shipping_threshold else 50
                        total = subtotal + shipping_cost
                        
                        print(f"AJAX cart update completed in {(time.time() - start_time)*1000:.2f}ms")
                        
                        from django.http import JsonResponse
                        return JsonResponse({
                            'success': True,
                            'subtotal': round(subtotal, 2),
                            'shipping_cost': shipping_cost,
                            'total': round(total, 2)
                        })
                except (ValueError, TypeError) as e:
                    print(f"Error processing quantity update: {e}")
    
    # Normal page display
    products = []
    subtotal = 0
    
    # Get all cart items with product data
    from .models import Product
    for item in cart:
        try:
            product_id = item.get('product_id')
            if not product_id or not str(product_id).isdigit():
                continue
                
            product = Product.objects.get(id=int(product_id))
            quantity = item['quantity']
            item_total = product.discounted_price * quantity
            
            products.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            
            subtotal += item_total
        except Exception as e:
            print(f"Error processing cart item: {e}")
    
    shipping_threshold = 1000
    shipping_cost = 0 if subtotal >= shipping_threshold else 50
    total = subtotal + shipping_cost
    
    return render(request, 'store/simple_cart.html', {
        'cart_items': products,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    })
