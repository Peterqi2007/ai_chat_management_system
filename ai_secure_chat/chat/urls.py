from django.urls import path
from . import views

urlpatterns = [
    # ===================== 分类路由 =====================
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/update/<int:pk>/', views.category_update, name='category_update'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),

    # ===================== 文件夹路由（支持按分类筛选） =====================
    path('folders/', views.folder_list, name='folder_list'),
    path('folders/category/<int:category_id>/', views.folder_list, name='folder_list_by_category'),
    path('folders/create/', views.folder_create, name='folder_create'),
    path('folders/update/<int:pk>/', views.folder_update, name='folder_update'),
    path('folders/delete/<int:pk>/', views.folder_delete, name='folder_delete'),

    # ===================== 对话路由（支持按文件夹筛选） =====================
    path('chats/', views.chat_entry_list, name='chat_entry_list'),
    path('chats/folder/<int:folder_id>/', views.chat_entry_list, name='chat_entry_list_by_folder'),
    path('chats/create/', views.chat_entry_create, name='chat_entry_create'),
    path('chats/update/<int:pk>/', views.chat_entry_update, name='chat_entry_update'),
    path('chats/delete/<int:pk>/', views.chat_entry_delete, name='chat_entry_delete'),

    # ===================== 核心对话功能 =====================
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chat/verify/<int:chat_id>/', views.private_chat_verify, name='private_chat_verify'),
    path('api/chat-stream/<int:chat_id>/', views.chat_stream, name='chat_stream'),

    # ===================== 用户资料 =====================
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]