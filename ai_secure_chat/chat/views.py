from django.http import StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from .models import ChatEntry, ChatMessage
from .services import stream_chat_completion


# 登录校验 + 仅允许POST请求
@login_required
@require_POST
def chat_stream(request, chat_id):
    # 获取对话条目（权限校验：只能访问自己的对话）
    chat_entry = get_object_or_404(ChatEntry, id=chat_id, user=request.user)
    # 获取用户输入的消息
    user_message = request.POST.get('message', '').strip()

    if not user_message:
        return StreamingHttpResponse(
            [f"data: {json.dumps({'error': '消息不能为空'})}\n\n"],
            content_type="text/event-stream"
        )

    # 生成器：SSE 流式响应
    def event_stream():
        full_ai_response = ""
        try:
            # 1. 先保存用户消息到数据库
            ChatMessage.objects.create(
                chat_entry=chat_entry,
                role="user",
                content=user_message
            )

            # 2. 调用千问流式API
            stream = stream_chat_completion(chat_entry, user_message)

            # 3. 逐块返回前端
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_ai_response += content
                    # 标准SSE格式传输
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # 4. 流式结束，保存AI回复到数据库
            ChatMessage.objects.create(
                chat_entry=chat_entry,
                role="assistant",
                content=full_ai_response
            )
            # 发送结束信号
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            # 错误返回
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # SSE 响应头配置（关键：禁止缓存、长连接）
    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Nginx 禁用缓冲
    return response