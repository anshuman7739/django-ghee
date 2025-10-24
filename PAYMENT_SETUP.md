# Payment QR Code Setup

## Important: Replace the Payment QR Code Image

The payment flow is now set up to show a QR code for UPI payments. However, you need to replace the placeholder image with your actual UPI payment QR code.

### Steps to Add Your QR Code:

1. **Generate Your UPI QR Code:**
   - Use your payment app (Google Pay, PhonePe, Paytm, etc.)
   - Go to "Receive Money" or "QR Code" section
   - Download or screenshot your QR code
   - Save it as a PNG or JPG file

2. **Replace the Placeholder:**
   - Navigate to: `store/static/store/images/`
   - Replace the file `payment-qr.png` with your actual QR code image
   - Make sure the filename remains `payment-qr.png` OR
   - Update the template files to use your new filename

3. **Image Recommendations:**
   - Format: PNG or JPG
   - Size: 300x300 pixels or larger (square format works best)
   - Quality: High resolution for better scanning
   - Background: White or transparent

### Payment Flow:

1. **Customer Journey:**
   - Customer adds items to cart
   - Proceeds to checkout
   - Enters shipping address
   - Selects payment method (COD or UPI)
   
2. **For UPI Payment:**
   - Customer is shown your QR code
   - They scan and pay using any UPI app
   - They click "I Have Paid" button
   - Order is created with `payment_status=True`
   
3. **For Cash on Delivery:**
   - Customer reviews order
   - Clicks "Place Order"
   - Order is created with `payment_status=False`

### Order Confirmation:

After successful payment (or COD selection), the customer receives:
- Order confirmation page
- Email confirmation (if configured)
- Order details with order number

### Admin Panel:

You can view all orders in the Django admin panel:
- Login to `/admin/`
- Navigate to Orders
- Filter by payment status (Paid/Unpaid)
- Filter by payment method (COD/UPI)

---

**Current Status:** ✅ Payment flow implemented, waiting for actual QR code image
