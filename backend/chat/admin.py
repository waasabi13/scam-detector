from django.contrib import admin
from .models import Message, FraudReport

admin.site.register(Message)
admin.site.register(FraudReport)