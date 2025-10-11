from django import template
register = template.Library()

@register.filter(name='to')
def to(value, arg):
    return range(value, arg+1)

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter(name='star_type')
def star_type(counter, rating):
    """
    Determine star type based on counter and rating.
    Returns 'full', 'half', or 'empty'.
    """
    try:
        rating = float(rating)
        full_stars = int(rating)
        decimal_part = rating - full_stars
        
        if counter <= full_stars:
            return 'full'
        elif counter == full_stars + 1 and decimal_part >= 0.5:
            return 'half'
        else:
            return 'empty'
    except (ValueError, TypeError):
        return 'empty'
        
@register.filter(name='has_size')
def has_size(product, size_id):
    """Check if a product has a particular size."""
    if not product or not hasattr(product, 'sizes'):
        return False
    try:
        return product.sizes.filter(id=size_id).exists()
    except Exception:
        return False

@register.filter(name='divided_by')
def divided_by(value, arg):
    """Divide the value by the arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
        
@register.filter(name='is_eligible_for_free_shipping')
def is_eligible_for_free_shipping(subtotal, threshold):
    """Check if the order is eligible for free shipping."""
    try:
        return float(subtotal) >= float(threshold)
    except (ValueError, TypeError):
        return False