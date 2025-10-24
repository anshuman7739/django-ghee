# 🧪 Quick Testing Guide - Payment Flow

## ✅ Testing Checklist

### Prerequisites:
- [x] Server running at http://127.0.0.1:8000/
- [x] QR code image in place (payment-qr.png)
- [x] Database has products

---

## 🔍 Test 1: UPI Payment Flow

### Steps:
1. **Open browser:** http://127.0.0.1:8000/
2. **Navigate to Shop:** Click "Shop" in navigation
3. **Add Product:** Click on any product → Select size → Add to Cart
4. **View Cart:** Click "Cart" in navigation
5. **Proceed to Checkout:** Click "Proceed to Checkout" button

### Expected at Step 1 (Shipping):
- ✅ 4-step progress indicator (Shipping → Payment → Review → Confirmation)
- ✅ Address form with all fields
- ✅ "Continue to Payment" button

6. **Fill Address Form:**
   - First Name: Test
   - Last Name: User
   - Email: test@example.com
   - Phone: 9876543210
   - Address: 123 Test Street
   - City: Mumbai
   - State: Maharashtra
   - Pincode: 400001

7. **Click "Continue to Payment"**

### Expected at Step 2 (Payment Method):
- ✅ Progress indicator shows step 2 active
- ✅ Two payment options visible:
  - Cash on Delivery (selected by default)
  - UPI Payment (Online)
- ✅ Order summary sidebar with totals

8. **Select "UPI Payment (Online)"**
9. **Click "Continue"**

### Expected at Step 3 (Payment QR):
- ✅ Progress indicator shows step 3 active
- ✅ PhonePe QR code displayed (large, centered)
- ✅ "ANSHUMAN" name visible on QR
- ✅ Total amount displayed: "Amount to Pay: ₹XXX.XX"
- ✅ Instructions: "Scan this QR code with any UPI app"
- ✅ Yellow info box with payment confirmation note
- ✅ Two buttons:
  - "Change Payment Method" (back)
  - "I Have Paid - Confirm Order" (green button)
- ✅ Order summary on right side

10. **Click "I Have Paid - Confirm Order"**

### Expected at Step 4 (Confirmation):
- ✅ Progress indicator shows step 4 active
- ✅ Green checkmark icon
- ✅ "Thank You for Your Order!" message
- ✅ Order number displayed
- ✅ Success message
- ✅ Cart badge shows 0 items
- ✅ Green success message at top

### Verify in Admin:
1. **Open:** http://127.0.0.1:8000/admin/
2. **Login** (create superuser if needed)
3. **Go to Orders**
4. **Check latest order:**
   - ✅ Payment method: "UPI Transfer"
   - ✅ Payment status: ✓ (checkmark/True)
   - ✅ Status: "Pending"
   - ✅ All order items present

---

## 🔍 Test 2: COD Payment Flow

### Steps:
1. **Add another product to cart**
2. **Go to Checkout**
3. **Fill address** (same as before or different)
4. **Click "Continue to Payment"**
5. **Keep "Cash on Delivery" selected** (default)
6. **Click "Continue"**

### Expected at Step 3 (Order Review):
- ✅ Progress indicator shows step 3 active
- ✅ "Review Your Order" heading
- ✅ Shipping details displayed in box:
  - Name, Email, Phone
  - Full address
- ✅ Payment method box:
  - "Cash on Delivery (COD)" with icon
  - "Pay with cash when you receive your order"
- ✅ Order summary on right
- ✅ Two buttons:
  - "Back to Payment"
  - "Place Order"

7. **Click "Place Order"**

### Expected at Step 4 (Confirmation):
- ✅ Same confirmation page as UPI flow
- ✅ Success message
- ✅ Order number
- ✅ Cart cleared

### Verify in Admin:
1. **Check latest order:**
   - ✅ Payment method: "Cash on Delivery"
   - ✅ Payment status: ✗ (unchecked/False)
   - ✅ Status: "Pending"

---

## 🔍 Test 3: Navigation & Back Buttons

### Test Back Navigation:
1. Start checkout
2. Fill address → Continue
3. **At Payment Method page:** Click "Back to Shipping"
   - ✅ Should return to address form
   - ✅ Form should be pre-filled with previous data
4. Continue to Payment again
5. Select UPI → Continue
6. **At QR Code page:** Click "Change Payment Method"
   - ✅ Should return to payment method selection
   - ✅ UPI should still be selected

### Test COD Back Navigation:
1. At Review page (COD flow)
2. Click "Back to Payment"
   - ✅ Should return to payment method selection
   - ✅ COD should still be selected

---

## 🔍 Test 4: Order Summary Accuracy

### Verify Calculations:
1. Add 2 different products with different quantities
2. Go through checkout
3. **Check at each step:**
   - ✅ Subtotal = sum of all items
   - ✅ Coupon discount shown (if applied)
   - ✅ Shipping cost:
     - Free if subtotal ≥ ₹1000
     - ₹50 if subtotal < ₹1000
   - ✅ Total = Subtotal - Discount + Shipping
   - ✅ All amounts match in sidebar at every step

---

## 🔍 Test 5: Account & Logout Features

### Test Account Page:
1. **Make sure you're logged in**
2. **Click "My Account" in navigation**
3. **Profile Tab:**
   - ✅ Username displayed
   - ✅ Email displayed
   - ✅ First name, last name
   - ✅ Member since date
4. **Orders Tab:**
   - ✅ Click "My Orders" in sidebar
   - ✅ All your orders listed
   - ✅ Payment status shown (Paid/Unpaid badge)
   - ✅ Order date, total, status
   - ✅ "View" button for each order

### Test Logout:
1. **Click "Logout" in navigation**
2. **Expected:**
   - ✅ Redirected to homepage
   - ✅ Success message: "Goodbye [username]! You have been logged out successfully."
   - ✅ Navigation shows "Login" instead of "Logout"
   - ✅ Session cleared

---

## 🔍 Test 6: Mobile Responsiveness

### Test on Mobile View:
1. **Open DevTools:** Press F12
2. **Toggle device toolbar:** Ctrl+Shift+M (Windows) or Cmd+Shift+M (Mac)
3. **Select mobile device:** iPhone 12 Pro / Samsung Galaxy S20
4. **Go through checkout:**
   - ✅ Forms are readable
   - ✅ QR code scales properly
   - ✅ Buttons are tappable
   - ✅ Order summary visible
   - ✅ Navigation works

---

## 🔍 Test 7: Error Scenarios

### Test Empty Cart:
1. **Go to:** http://127.0.0.1:8000/checkout/
2. **Expected:**
   - ✅ Warning message: "Your cart is empty..."
   - ✅ Redirected to cart page

### Test Invalid Form:
1. Start checkout
2. Leave required fields empty
3. Click Continue
4. **Expected:**
   - ✅ Alert: "Please fill in all required fields correctly."
   - ✅ Invalid fields highlighted

### Test Invalid Phone:
1. Enter phone: "12345" (less than 10 digits)
2. Click Continue
3. **Expected:**
   - ✅ Validation error
   - ✅ Field highlighted

---

## 📊 Success Metrics

### All Tests Passing:
- [x] UPI flow completes successfully
- [x] COD flow completes successfully
- [x] QR code displays properly
- [x] Payment status tracked correctly
- [x] Back navigation works
- [x] Order summary accurate
- [x] Account page shows orders
- [x] Logout works properly
- [x] Mobile responsive
- [x] Error handling works

---

## 🐛 Common Issues & Fixes

### Issue: QR Code Not Showing
**Fix:**
```bash
# Check if file exists
ls -lh store/static/store/images/payment-qr.png

# If missing, copy again
cp "/path/to/your/qr.png" store/static/store/images/payment-qr.png
```

### Issue: Orders Not Creating
**Fix:**
1. Check terminal for errors
2. Check if products exist in database
3. Verify cart has items
4. Check session data in browser DevTools

### Issue: Payment Status Not Updating
**Fix:**
1. Check POST data includes `payment_verified` field
2. Verify form in template has hidden input
3. Check server logs

---

## 📸 Screenshots to Take

For documentation/testing evidence:
1. ✅ Payment method selection page
2. ✅ QR code payment page (with QR visible)
3. ✅ Order review page (COD)
4. ✅ Order confirmation page
5. ✅ Admin panel showing orders with payment status
6. ✅ Account page with orders

---

## 🎯 Production Checklist

Before going live:
- [ ] Test with real UPI payment
- [ ] Verify QR code is correct
- [ ] Set up email notifications
- [ ] Enable HTTPS
- [ ] Test payment verification workflow
- [ ] Train staff on payment verification
- [ ] Set up payment reconciliation process
- [ ] Configure backup payment options
- [ ] Test error scenarios
- [ ] Monitor first few orders closely

---

**Testing Date:** October 14, 2025  
**Status:** Ready for Testing ✅  
**Server:** http://127.0.0.1:8000/
