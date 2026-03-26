from django.urls import path
from . import views

urlpatterns = [
    # 流式对话接口
    path('api/chat-stream/<int:chat_id>/', views.chat_stream, name='chat_stream'),
]