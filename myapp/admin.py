from django.contrib import admin
from .models import *

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)
admin.site.register(Feedback)

# super acc
# Username: alec
# Email Address: alec@gmail.com
# Password: alectest