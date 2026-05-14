from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_fraud = models.BooleanField(default=False)
    fraud_confidence = models.FloatField(null=True, blank=True)


class FraudReport(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fraud_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    is_reviewed = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(null=True, blank=True)
