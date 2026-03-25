from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from datetime import date
from .models import CustomUser


@api_view(['POST'])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    display_name = request.data.get('display_name')
    birth_date = request.data.get('birth_date')  # ISO format: 'YYYY-MM-DD'

    if not all([username, password, display_name, birth_date]):
        return Response({'error': 'Все поля обязательны'}, status=400)

    if CustomUser.objects.filter(username=username).exists():
        return Response({'error': 'Логин уже занят'}, status=400)

    if len(password) < 8:
        return Response({'error': 'Пароль слишком короткий'}, status=400)

    try:
        parsed_date = date.fromisoformat(birth_date)
        if parsed_date > date.today():
            return Response({'error': 'Дата рождения не может быть в будущем'}, status=400)
    except ValueError:
        return Response({'error': 'Неверный формат даты'}, status=400)

    user = CustomUser.objects.create_user(
        username=username,
        password=password,
        display_name=display_name,
        birth_date=parsed_date
    )
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'username': user.username,
        'display_name': user.display_name,
        'user_id': user.id,
    })


@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Неверные данные для входа'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'username': user.username,
        'display_name': user.display_name,
        'user_id': user.id,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.GET.get('q', '')
    users = CustomUser.objects.filter(display_name__icontains=query).exclude(id=request.user.id)
    return Response([
        {'id': u.id, 'username': u.username, 'display_name': u.display_name}
        for u in users
    ])


@api_view(['GET'])
def check_username(request):
    username = request.GET.get('username', '')
    exists = CustomUser.objects.filter(username=username).exists()
    return Response({'taken': exists})
