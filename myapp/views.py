from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import datetime

from .models import Customer, Order, OrderItem, Product, ShippingAddress, Feedback


@receiver(post_save, sender=User)
def create_customer(sender, instance, created, **kwargs):
    if created:  # Only create the customer if the user was newly created
        customer = Customer.objects.create(user=instance)
        customer.name = instance.username  # Set the name to the username
        customer.email = instance.email    # Set the email to the user's email
        customer.save()

@receiver(post_save, sender=User)
def save_customer(sender, instance, **kwargs):
    try:
        instance.customer.save()  # Save the associated customer object
    except Customer.DoesNotExist:
        pass  # No action if customer does not exist

def home(request):
    if request.user.is_authenticated:
        # Ensure the customer exists for the logged-in user
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items  # Get the cart item count
    else:
        cartItems = 0  # If user is not authenticated, set cart items to 0

    return render(request, 'home.html', {'cartItems': cartItems})


# Login view
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect('home')  # Redirect to home after successful login
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')  # Stay on login page with error message
    
    return render(request, 'login.html')

# Registration view
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
        
        # Create the user
        user = User.objects.create_user(username=username, email=email, password=password)
        
        auth_login(request, user)
        return redirect('home')  # Redirect to the homepage after successful registration
    
    return render(request, 'login.html')

def logout_user(request):
    logout(request)  # Logs out the current user
    return redirect('login')  # Redirects to the home page after logging out

def aboutus(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items  # Get the cart item count
    else:
        cartItems = 0  # If user is not authenticated, set cart items to 0

    context = {
        'cartItems': cartItems
    }
    return render(request, 'aboutus.html', context)

def myorder(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        
        # Get the customer's order (incomplete or completed) or return None if it doesn't exist
        order = Order.objects.filter(customer=customer, complete=False).first()
        
        # If an order exists, use its cart items, otherwise set cartItems to 0
        if order:
            cartItems = order.get_cart_items
        else:
            cartItems = 0
        
        # Retrieve the user's completed orders
        orders = Order.objects.filter(customer=customer, complete=True)
    else:
        orders = []
        cartItems = 0  # If user is not authenticated, cartItems should be 0

    context = {
        'orders': orders,
        'cartItems': cartItems,
    }
    return render(request, 'myorder.html', context)


def cart(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order.get_cart_items

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'cart.html', context)


def checkout(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'shipping': False}
        cartItems = order['get_cart_items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'checkout.html', context)


# Update cart items (this will handle add/remove items from the cart)
def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    
    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    
    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        if total == order.get_cart_total:
            order.complete = True
            order.save()

        if data['shipping']:  # Check if shipping information exists
            shipping_data = data['shipping']
            shipping_address = ShippingAddress.objects.create(
                customer=customer,
                order=order,
                address=shipping_data['address'],
                city=shipping_data['city'],
                state=shipping_data['state'],
                zipcode=shipping_data['zipcode'],
            )
            shipping_address.save()

        return JsonResponse({'message': 'Order placed successfully!'}, safe=False)

    else:
        return JsonResponse({'error': 'User is not logged in'}, safe=False)
    
def products(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']

    # Get the search query from the GET parameters (if any)
    search_query = request.GET.get('search', '')
    if search_query:
        # Filter products based on the search query (case-insensitive partial match)
        products = Product.objects.filter(name__icontains=search_query)
    else:
        # If no search query, show all products
        products = Product.objects.all()

    context = {
        'products': products,
        'cartItems': cartItems,
        'search_query': search_query  # Optionally, pass the search query back to the template
    }
    return render(request, 'products.html', context)


def product_list(request):
    search_query = request.GET.get('search', '')  # Get the search query from the URL parameter
    if search_query:
        products = Product.objects.filter(name__icontains=search_query)  # Filter products based on the search term
    else:
        products = Product.objects.all()  # Show all products if no search query is provided

    return render(request, 'product_list.html', {'products': products})

def feedback(request):
    if request.method == 'POST':
        # Process the feedback form
        message = request.POST.get('message', '')
        screenshots = request.FILES.getlist('screenshots')

        if message:  # Ensure the message is provided
            if request.user.is_authenticated:
                customer = request.user.customer  # Get the logged-in customer's instance
                feedback = Feedback.objects.create(
                    customer=customer,
                    message=message,
                )
                # Save each uploaded screenshot
                for file in screenshots:
                    feedback.screenshots.save(file.name, file, save=True)
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'User not authenticated.'})
        else:
            return JsonResponse({'success': False, 'error': 'Message is required.'})

    # For GET request, render the feedback form
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
        items = order.orderitem_set.all()
    else:
        cartItems = 0
        items = []

    context = {
        'cartItems': cartItems,
        'items': items
    }
    return render(request, 'feedback.html', context)


