def cart_context(request):
    """
    Context processor to add cart count to all templates
    """
    cart = request.session.get('cart', [])
    cart_count = sum(item.get('quantity', 0) for item in cart if isinstance(item, dict))
    return {
        'cart_count': cart_count
    }
