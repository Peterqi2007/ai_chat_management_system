from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Category, Folder, ChatEntry, UserProfile,ChatMessage
from .forms import (
    CategoryForm, FolderForm, ChatEntryForm,
    PrivacyPasswordVerifyForm, #UserProfileForm
)
# 保留你已有的流式对话视图
from django.http import StreamingHttpResponse
from .services import stream_chat_completion
import json


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



# ==============================================
# 1. 分类列表视图 ✅【Claude优化版：加载关联文件夹】
# ==============================================
@login_required
def category_list(request):
    """分类列表 - 显示分类及其下的所有文件夹"""
    categories = Category.objects.filter(
        user=request.user
    ).prefetch_related('folders').order_by('order', '-created_at')
    return render(request, 'chat/category_list.html', {'categories': categories})

# ==============================================
# 2. 分类增删改查（无修改，保留原有）
# ==============================================
@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, '分类创建成功！')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'chat/category_form.html', {'form': form, 'title': '创建分类'})

@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '分类更新成功！')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'chat/category_form.html', {'form': form, 'title': '编辑分类'})

@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    category.delete()
    messages.success(request, '分类删除成功！')
    return redirect('category_list')

# ==============================================
# 3. 文件夹列表视图 ✅【Claude优化版：分类过滤+子文件夹+对话】
# ==============================================
@login_required
def folder_list(request, category_id=None):
    """文件夹列表 - 支持按分类过滤，显示子文件夹和对话条目"""
    if category_id:
        # 按分类筛选文件夹
        folders = Folder.objects.filter(
            user=request.user,
            category_id=category_id
        ).prefetch_related('child_folders', 'chat_entries').order_by('order', '-created_at')
        category = get_object_or_404(Category, id=category_id, user=request.user)
    else:
        # 只显示顶级文件夹（无父文件夹）
        folders = Folder.objects.filter(
            user=request.user,
            parent_folder__isnull=True
        ).prefetch_related('child_folders', 'chat_entries').order_by('order', '-created_at')
        category = None

    return render(request, 'chat/folder_list.html', {
        'folders': folders,
        'category': category
    })

# ==============================================
# 4. 文件夹增删改查（无修改，保留原有）
# ==============================================
@login_required
def folder_create(request):
    if request.method == 'POST':
        form = FolderForm(request.POST, user=request.user)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            folder.save()
            messages.success(request, '文件夹创建成功！')
            return redirect('folder_list')
    else:
        form = FolderForm(user=request.user)
    return render(request, 'chat/folder_form.html', {'form': form, 'title': '创建文件夹'})

@login_required
def folder_update(request, pk):
    folder = get_object_or_404(Folder, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FolderForm(request.POST, user=request.user, instance=folder)
        if form.is_valid():
            form.save()
            messages.success(request, '文件夹更新成功！')
            return redirect('folder_list')
    else:
        form = FolderForm(user=request.user, instance=folder)
    return render(request, 'chat/folder_form.html', {'form': form, 'title': '编辑文件夹'})

@login_required
def folder_delete(request, pk):
    folder = get_object_or_404(Folder, pk=pk, user=request.user)
    folder.delete()
    messages.success(request, '文件夹删除成功！')
    return redirect('folder_list')

# ==============================================
# 5. 对话条目列表视图 ✅【Claude优化版：按文件夹过滤+上下文】
# ==============================================
@login_required
def chat_entry_list(request, folder_id=None):
    """对话列表 - 支持按文件夹筛选，显示所属文件夹信息"""
    if folder_id:
        # 按文件夹筛选对话
        folder = get_object_or_404(Folder, id=folder_id, user=request.user)
        chat_entries = ChatEntry.objects.filter(
            user=request.user,
            folder_id=folder_id
        ).order_by('-updated_at')
    else:
        # 显示所有对话
        folder = None
        chat_entries = ChatEntry.objects.filter(
            user=request.user
        ).order_by('-updated_at')

    return render(request, 'chat/chat_entry_list.html', {
        'chat_entries': chat_entries,
        'folder': folder
    })

@login_required
def chat_verify_privacy(request, chat_id):
    """独立的隐私密码验证页面，强制重定向访问"""
    chat_entry = get_object_or_404(ChatEntry, id=chat_id, user=request.user)
    profile = get_object_or_404(UserProfile, user=request.user)
    session_key = f'private_chat_verified_{chat_id}'

    # 已验证直接返回信息页
    if request.session.get(session_key):
        return redirect('chat_entry_info', chat_id=chat_id)

    if request.method == 'POST':
        form = PrivacyPasswordVerifyForm(request.POST)
        if form.is_valid():
            pwd = form.cleaned_data['privacy_password']
            # 验证密码（你模型中的哈希验证方法）
            if profile.check_privacy_password(pwd):
                request.session[session_key] = True
                # 验证通过 → 跳回对话信息页
                return redirect('chat_entry_info', chat_id=chat_id)
            form.add_error('privacy_password', '密码错误，请重试！')
    else:
        form = PrivacyPasswordVerifyForm()

    return render(request, 'chat/private_verify.html', {
        'form': form,
        'chat_entry': chat_entry
    })

# ====================== 修正：对话信息页（隐私校验=重定向到验证URL）======================
@login_required
def chat_entry_info(request, chat_id):
    chat_entry = get_object_or_404(ChatEntry, id=chat_id, user=request.user)
    session_key = f'private_chat_verified_{chat_id}'

    # ✅ 核心修正：隐私对话 + 未验证 → 强制重定向到独立验证URL
    if chat_entry.is_private and not request.session.get(session_key, False):
        return redirect('chat_verify_privacy', chat_id=chat_id)

    # 标记：从info页准备进入对话（用于chat_detail权限校验）
    request.session[f'from_info_{chat_id}'] = True

    context = {
        # 核心对象
        'chat_entry': chat_entry,
        # 关键字（Mezzanine格式）
        'keywords': chat_entry.keywords.keywords,
        # 关联文件夹
        'folder': chat_entry.folder,
        # 基础信息
        'title': chat_entry.title,
        'description': chat_entry.description,
        'is_private': chat_entry.is_private,
        # 模型参数
        'temperature': chat_entry.temperature,
        'top_p': chat_entry.top_p,
        'max_tokens': chat_entry.max_tokens,
        # 时间信息（格式化）
        'created_at': chat_entry.created_at,
        'updated_at': chat_entry.updated_at,
        # 页面配置
        'page_title': f"对话详情 - {chat_entry.title}",

    }

    return render(request, 'chat/chat_entry_info.html', context)


# ==============================================
# 6. 对话条目增删改查（无修改，保留原有）
# ==============================================
@login_required
def chat_entry_create(request):
    if request.method == 'POST':
        form = ChatEntryForm(request.POST, user=request.user)
        if form.is_valid():
            chat_entry = form.save(commit=False)
            chat_entry.user = request.user
            chat_entry.system_prompt = "你是一个智能助手"
            chat_entry.save()
            messages.success(request, '对话创建成功！')
            return redirect('chat_detail', chat_id=chat_entry.id)
    else:
        form = ChatEntryForm(user=request.user)
    return render(request, 'chat/chat_entry_form.html', {'form': form, 'title': '创建对话'})

@login_required
def chat_entry_update(request, pk):
    chat_entry = get_object_or_404(ChatEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ChatEntryForm(request.POST, user=request.user, instance=chat_entry)
        if form.is_valid():
            form.save()
            messages.success(request, '对话更新成功！')
            return redirect('chat_entry_list')
    else:
        form = ChatEntryForm(user=request.user, instance=chat_entry)
    return render(request, 'chat/chat_entry_form.html', {'form': form, 'title': '编辑对话'})

@login_required
def chat_entry_delete(request, pk):
    chat_entry = get_object_or_404(ChatEntry, pk=pk, user=request.user)
    chat_entry.delete()
    messages.success(request, '对话删除成功！')
    return redirect('chat_entry_list')

# ==============================================
# 7. 隐私对话验证、对话详情、用户资料、流式对话（无修改，保留原有）
# ==============================================
@login_required
def private_chat_verify(request, chat_id):
    chat_entry = get_object_or_404(ChatEntry, id=chat_id, user=request.user, is_private=True)
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = PrivacyPasswordVerifyForm(request.POST)
        if form.is_valid():
            import hashlib
            pwd = form.cleaned_data['privacy_password']
            pwd_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
            if pwd_hash == profile.privacy_password_hash:
                request.session[f'private_chat_{chat_id}'] = True
                return redirect('chat_detail', chat_id=chat_id)
            else:
                form.add_error('privacy_password', '密码错误，请重试！')
    else:
        form = PrivacyPasswordVerifyForm()
    return render(request, 'chat/private_verify.html', {'form': form, 'chat_entry': chat_entry})

@login_required
def chat_detail(request, chat_id):
    chat_entry = get_object_or_404(ChatEntry, id=chat_id, user=request.user)

    # ✅ 核心限制：仅允许从 chat_entry_info 跳转进入，禁止直接输URL访问
    if not request.session.get(f'from_info_{chat_id}', False):
        messages.error(request, "禁止直接访问！请从对话详情页进入")
        return redirect('chat_entry_info', chat_id=chat_id)

    # 隐私对话二次校验（兜底）
    if chat_entry.is_private and not request.session.get(f'private_chat_verified_{chat_id}', False):
        return redirect('chat_verify_privacy', chat_id=chat_id)

    # 清理临时标记（防止重复使用）
    del request.session[f'from_info_{chat_id}']

    #if chat_entry.is_private:
        #if not request.session.get(f'private_chat_{chat_id}', False):
            #return redirect('private_chat_verify', chat_id=chat_id)
    chat_messages = chat_entry.messages.all().order_by('created_at')
    return render(request, 'chat/chat_detail.html', {
        'chat_entry': chat_entry,
        'messages': chat_messages
    })
'''
@login_required
def profile_edit(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '资料更新成功！')
            return redirect('category_list')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'chat/profile_edit.html', {'form': form, 'title': '个人资料'})

'''


