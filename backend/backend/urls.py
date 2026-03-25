from django.contrib import admin
from django.urls import path
from users import views as user_views
from chat import views as chat_views
from detector import views as detector_views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/register/', user_views.register),
    path('api/login/', user_views.login),
    path('api/users/search/', user_views.search_users),
    path('api/users/check_username/', user_views.check_username),

    path('api/chats/', chat_views.get_dialogs),  # ✅ Только один этот оставить
    path('api/messages/<int:user_id>/send/', chat_views.send_message),
    path('api/messages/<int:user_id>/', chat_views.get_messages),

    path('api/classify/', detector_views.classify_message),
]

