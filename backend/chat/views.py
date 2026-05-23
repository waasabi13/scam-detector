from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Message, FraudReport
from users.models import CustomUser
from django.db.models import Q
from detector.fraud_detector import FraudDetector
from detector.speech_utils import transcribe_audio, clean_transcript
from detector.fraud_detector import FraudDetector

fraud_detector = FraudDetector()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, user_id):
    text = request.data.get('text')
    if not text:
        return Response({'error': 'Empty message'}, status=400)

    recipient = get_object_or_404(CustomUser, id=user_id)

    label, confidence = fraud_detector.classify_message(text)
    is_fraud = label.lower().startswith("мошенничество")

    message = Message.objects.create(
        sender=request.user,
        recipient=recipient,
        text=text,
        is_fraud=is_fraud,
        fraud_confidence=confidence
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

    messages = Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).order_by('-timestamp')

    dialogs = {}

    for msg in messages:
        other_user = msg.recipient if msg.sender == user else msg.sender

        if other_user.id not in dialogs:
            unread_count = Message.objects.filter(
                sender=other_user,
                recipient=user,
                is_read=False
            ).count()

            dialogs[other_user.id] = {
                'id': other_user.id,
                'username': other_user.username,
                'display_name': other_user.display_name,
                'last_message_time': msg.timestamp,
                'unread_count': unread_count,
            }

    return Response(list(dialogs.values()))

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
        response.append({
            'id': m.id,
            'text': m.text,
            'timestamp': m.timestamp,
            'sender': m.sender.username,
            'isRead': m.is_read,
            'audio_url': request.build_absolute_uri(m.audio.url) if m.audio else None,
            'message_type': m.message_type,
            'transcript': m.transcript,
            'is_fraud': m.is_fraud if m.recipient == request.user else False,
            'fraud_confidence': m.fraud_confidence if m.recipient == request.user else None
        })

    return Response(response)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_voice_message(request, user_id):
    recipient = get_object_or_404(CustomUser, id=user_id)
    audio = request.FILES.get('audio')

    if not audio:
        return Response({'error': 'Audio file is required'}, status=400)

    message = Message.objects.create(
        sender=request.user,
        recipient=recipient,
        audio=audio,
        text='Голосовое сообщение',
        message_type='voice'
    )

    return Response({
        'id': message.id,
        'text': message.text,
        'message_type': message.message_type,
        'audio_url': request.build_absolute_uri(message.audio.url),
        'timestamp': message.timestamp,
        'sender': request.user.username,
        'isRead': message.is_read,
        'is_fraud': False,
        'fraud_confidence': None,
        'transcript': ''
    })
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_voice_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    if message.message_type != 'voice':
        return Response({'error': 'Сообщение не является голосовым'}, status=400)

    if not message.audio:
        return Response({'error': 'У сообщения отсутствует аудиофайл'}, status=400)

    transcript = transcribe_audio(message.audio.path)
    cleaned_text = clean_transcript(transcript)

    label, confidence = fraud_detector.classify_message(cleaned_text)

    message.transcript = cleaned_text
    message.is_fraud = label.lower().startswith("мошенничество")
    message.fraud_confidence = round(confidence, 2)
    message.save()

    return Response({
        'id': message.id,
        'transcript': message.transcript,
        'is_fraud': message.is_fraud,
        'fraud_confidence': message.fraud_confidence,
    })

from .models import Message, FraudReport

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    FraudReport.objects.create(
        message=message,
        reported_by=request.user
    )

    return Response({'status': 'reported'})