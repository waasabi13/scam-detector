from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('voice', 'Voice'),
    )

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(blank=True)
    audio = models.FileField(upload_to='voice_messages/', null=True, blank=True)
    transcript = models.TextField(blank=True, default='')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_fraud = models.BooleanField(default=False)
    fraud_confidence = models.FloatField(null=True, blank=True)


class FraudReport(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fraud_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(null=True, blank=True)
