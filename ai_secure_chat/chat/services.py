from openai import OpenAI
from django.conf import settings
from .models import UserProfile, ChatEntry, ChatMessage

# ==============================================
# 千问API 核心配置（固定，官方要求）
# ==============================================
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"  # 默认千问模型


# ==============================================
# 1. 获取千问客户端（核心：读取用户自己的API Key）
# 从 UserProfile 中获取用户存储的 api_key
# ==============================================
def get_qwen_client(user):
    """
    根据当前用户，获取专属的千问API客户端
    :param user: Django User 对象
    :return: OpenAI 客户端实例
    """
    try:
        # 获取用户的扩展资料
        profile = UserProfile.objects.get(user=user)
        # 校验用户是否配置了API Key
        if not profile.api_key:
            raise ValueError("请先在个人资料中配置千问API Key！")

        # 初始化千问客户端（官方标准写法）
        client = OpenAI(
            api_key=profile.api_key,
            base_url=QWEN_BASE_URL
        )
        return client

    except UserProfile.DoesNotExist:
        raise ValueError("用户资料不存在，请先创建用户资料！")


# ==============================================
# 2. 流式对话生成（项目核心需求：前端实时输出）
# 传入对话条目ChatEntry，自动加载所有配置+历史消息
# 返回生成器，支持SSE流式响应
# ==============================================
def stream_chat_completion(chat_entry: ChatEntry, user_message: str):
    """
    千问流式对话
    :param chat_entry: 对话条目对象（携带系统提示词、模型参数）
    :param user_message: 用户最新输入的消息
    :return: 流式响应生成器
    """
    # 1. 获取客户端
    client = get_qwen_client(chat_entry.user)

    # 2. 构建消息列表（系统提示词 + 历史对话 + 当前用户消息）
    messages = []

    # 系统提示词（来自 ChatEntry 模型）
    messages.append({
        "role": "system",
        "content": chat_entry.system_prompt
    })

    # 历史对话消息（按时间正序，来自 ChatMessage 模型）
    for msg in chat_entry.messages.all():
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # 用户最新提问
    messages.append({
        "role": "user",
        "content": user_message
    })

    # 3. 调用千问流式API（官方标准参数）
    try:
        stream = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=chat_entry.temperature,
            top_p=chat_entry.top_p,
            max_tokens=chat_entry.max_tokens,
            stream=True  # 开启流式输出
        )
        return stream

    except Exception as e:
        raise Exception(f"千问API调用失败：{str(e)}")


# ==============================================
# 3. 普通非流式对话（备用接口）
# ==============================================
def chat_completion(chat_entry: ChatEntry, user_message: str):
    """
    千问非流式对话（备用）
    """
    client = get_qwen_client(chat_entry.user)

    messages = [
        {"role": "system", "content": chat_entry.system_prompt}
    ]
    for msg in chat_entry.messages.all():
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=chat_entry.temperature,
            top_p=chat_entry.top_p,
            max_tokens=chat_entry.max_tokens,
            stream=False
        )
        return completion.choices[0].message.content

    except Exception as e:
        raise Exception(f"千问API调用失败：{str(e)}")