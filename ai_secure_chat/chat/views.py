from django.shortcuts import render

# Create your views here.

from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Conversation
from .services import minimax_stream_chat
import json

@login_required
def stream_chat_message(request):
    """
    流式对话接口
    前端 POST 发送：conversation_id, message
    返回：流式文本流
    """
    if request.method != "POST":
        return StreamingHttpResponse(json.dumps({"error": "请求方法错误"}), content_type="application/json")

    # 获取参数
    conv_id = request.POST.get("conversation_id")
    user_message = request.POST.get("content", "").strip()
    conversation = get_object_or_404(Conversation, id=conv_id, user=request.user)

    # 1. 构建对话历史（从数据库读取）
    messages = []
    for msg in conversation.messages.all().order_by("timestamp"):
        messages.append({"role": msg.role, "content": msg.content})
    # 添加当前用户消息
    messages.append({"role": "user", "content": user_message})

    # 2. 调用流式服务（可自定义参数）
    stream_generator = minimax_stream_chat(
        messages=messages,
        temperature=0.7,  # 可按对话分类动态调整
        max_tokens=2048
    )

    # 3. 返回 Django 流式响应
    return StreamingHttpResponse(
        stream_generator,
        content_type="text/plain; charset=utf-8"
    )
