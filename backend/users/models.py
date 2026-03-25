from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    display_name = models.CharField(max_length=50, default='Пользователь')
    birth_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.username

