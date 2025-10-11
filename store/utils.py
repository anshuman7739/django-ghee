"""Utility functions for the store app."""

def track_recently_viewed(request, product_id):
    """Track recently viewed products.
    
    This function adds a product to the user's recently viewed products list.
    The list is stored in the session and has a maximum length of 10 products.
    """
    recently_viewed = request.session.get('recently_viewed', [])
    
    # Convert to integers if needed
    recently_viewed = [int(id) if isinstance(id, str) else id for id in recently_viewed]
    
    # Remove the product if it's already in the list
    if product_id in recently_viewed:
        recently_viewed.remove(product_id)
    
    # Add the product to the beginning of the list
    recently_viewed.insert(0, product_id)
    
    # Keep only the 10 most recent products
    recently_viewed = recently_viewed[:10]
    
    # Update the session
    request.session['recently_viewed'] = recently_viewed
    request.session.modified = True
