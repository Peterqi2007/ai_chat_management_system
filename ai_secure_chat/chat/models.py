import mezzanine.core.models
from django.db import models
from django.contrib.auth.models import User
from mezzanine.pages.models import Page


# 1. 对话分类模型
class ConversationCategory(mezzanine.core.models.Orderable):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 可以继承 Mezzanine 的 Orderable 来实现拖拽排序


# 2. 对话会话模型
class Conversation(models.Model):
    title = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    category = models.ForeignKey(ConversationCategory, null=True, blank=True, on_delete=models.SET_NULL)

    # 核心需求：密码控制查看
    is_hidden = models.BooleanField(default=False)
    view_password = models.CharField(max_length=128, blank=True, null=True)  # 建议存入加密后的哈希值

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# 3. 对话消息模型
class Message(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'AI'),
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)