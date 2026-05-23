from django.contrib import admin
from django.urls import path
from users import views as user_views
from chat import views as chat_views
from detector import views as detector_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/register/', user_views.register),
    path('api/login/', user_views.login),
    path('api/users/search/', user_views.search_users),
    path('api/users/check_username/', user_views.check_username),
    path('admin/', admin.site.urls),
    path('api/chats/', chat_views.get_dialogs),
    path('api/messages/<int:user_id>/send/', chat_views.send_message),
    path('api/messages/<int:user_id>/', chat_views.get_messages),
    path('api/messages/<int:message_id>/report/', chat_views.report_message),
    path('api/classify/', detector_views.classify_message),
    path('api/messages/<int:user_id>/send-voice/', chat_views.send_voice_message),
    path('api/messages/<int:message_id>/check-voice/', chat_views.check_voice_message),
]



urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)