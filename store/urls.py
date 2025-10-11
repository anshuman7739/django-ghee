from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('old/', views.homepage_old, name='homepage_old'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('simple_cart/', views.simple_cart, name='simple_cart'),  # New simple cart view
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='homepage'), name='logout'),
    path('contact/', views.contact, name='contact'),
    path('contact-new/', views.contact_new, name='contact_new'),
    path('about/', views.about, name='about'),
    path('newsletter-subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('search/', views.search_products, name='search_products'),
    path('benefits/', views.benefits, name='benefits'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
]
