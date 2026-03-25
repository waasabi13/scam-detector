from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Message
from users.models import CustomUser
from django.db.models import Q


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, user_id):
    text = request.data.get('text')
    if not text:
        return Response({'error': 'Empty message'}, status=400)

    recipient = get_object_or_404(CustomUser, id=user_id)

    message = Message.objects.create(
        sender=request.user,
        recipient=recipient,
        text=text
    )

    return Response({
        'id': message.id,
        'text': message.text,
        'timestamp': message.timestamp,
        'sender': request.user.username,  # <== ключевая строчка
        'isRead': message.is_read,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_partners(request):
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    )

    user_ids = set()
    for msg in messages:
        if msg.sender != request.user:
            user_ids.add(msg.sender.id)
        if msg.recipient != request.user:
            user_ids.add(msg.recipient.id)

    users = CustomUser.objects.filter(id__in=user_ids)
    return Response([
        {'id': u.id, 'username': u.username, 'display_name': u.display_name}
        for u in users
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dialogs(request):
    user = request.user
    sent = Message.objects.filter(sender=user).values_list('recipient', flat=True)
    received = Message.objects.filter(recipient=user).values_list('sender', flat=True)
    user_ids = set(sent) | set(received)

    users = CustomUser.objects.filter(id__in=user_ids)
    return Response([
        {'id': u.id, 'username': u.username, 'display_name': u.display_name}
        for u in users
    ])

from detector.fraud_detector import FraudDetector

fraud_detector = FraudDetector()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)

    messages = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).order_by('timestamp')

    # Отмечаем как прочитанные
    Message.objects.filter(
        sender=other_user,
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    response = []
    for m in messages:
        fraud_info = {}
        if m.sender != request.user:
            label, confidence = fraud_detector.classify_message(m.text)
            if label.lower().startswith("мошенничество"):
                fraud_info = {
                    'is_fraud': True,
                    'fraud_label': label,
                    'fraud_confidence': round(confidence, 2)
                }

        response.append({
            'id': m.id,
            'text': m.text,
            'timestamp': m.timestamp,
            'sender': m.sender.username,  # теперь только sender
            'isRead': m.is_read,
            **fraud_info
        })

    return Response(response)





