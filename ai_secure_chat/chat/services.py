from openai import OpenAI
# 导入 OpenAI 细分异常类（精准捕获不同错误类型）
from openai import (
    APIError,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    NotFoundError
)
from django.conf import settings
from .models import UserProfile, ChatEntry, ChatMessage
import logging

# 配置日志（便于排查请求链路问题）
logger = logging.getLogger(__name__)

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

        # 校验用户是否配置了API Key（细化空值提示）
        if not profile.api_key:
            error_msg = "用户未配置千问API Key：请前往个人资料页填写有效的API Key"
            logger.error(f"[千问客户端初始化失败] {error_msg} | 用户ID: {user.id}")
            raise ValueError(error_msg)

        # 校验API Key格式（基础校验，避免明显无效的Key）
        if len(profile.api_key.strip()) < 10:  # 千问API Key长度远大于10，基础过滤
            error_msg = "千问API Key格式无效：请检查是否复制完整的API Key（长度过短）"
            logger.error(f"[千问客户端初始化失败] {error_msg} | 用户ID: {user.id}")
            raise ValueError(error_msg)

        # 初始化千问客户端（官方标准写法）
        client = OpenAI(
            api_key=profile.api_key,
            base_url=QWEN_BASE_URL
        )
        logger.info(f"[千问客户端初始化成功] 用户ID: {user.id}")
        return client

    except UserProfile.DoesNotExist:
        error_msg = f"用户资料不存在：用户ID {user.id} 未创建个人资料，请先完成资料创建"
        logger.error(f"[千问客户端初始化失败] {error_msg}")
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"千问客户端初始化异常：{str(e)}"
        logger.error(f"[千问客户端初始化失败] {error_msg} | 用户ID: {user.id}")
        raise Exception(error_msg)


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
    user_id = chat_entry.user.id
    chat_entry_id = chat_entry.id
    logger.info(f"[开始流式对话请求] 对话ID: {chat_entry_id} | 用户ID: {user_id}")

    # 1. 获取客户端
    try:
        client = get_qwen_client(chat_entry.user)
    except (ValueError, Exception) as e:
        raise Exception(f"客户端初始化失败：{str(e)}")

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

    # 3. 调用千问流式API（细化异常捕获）
    try:
        logger.info(f"[调用千问流式API] 模型: {DEFAULT_MODEL} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        stream = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=chat_entry.temperature,
            top_p=chat_entry.top_p,
            max_tokens=chat_entry.max_tokens,
            stream=True  # 开启流式输出
        )
        logger.info(f"[千问流式API请求成功] 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        return stream

    # 细分OpenAI异常类型，返回精准错误信息
    except AuthenticationError as e:
        error_msg = f"API Key认证失败：{str(e)} | 请检查API Key是否有效（如过期、权限不足）"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except RateLimitError as e:
        error_msg = f"API额度/限流触发：{str(e)} | 请检查千问API额度是否耗尽，或是否触发频率限制"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except APIConnectionError as e:
        error_msg = f"API网络连接失败：{str(e)} | 请检查网络是否正常，或千问API服务是否可用"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except NotFoundError as e:
        error_msg = f"模型/接口不存在：{str(e)} | 当前使用模型 {DEFAULT_MODEL} 可能未开通，请检查模型权限"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except APIError as e:
        error_msg = f"千问API服务异常：{str(e)} | 请稍后重试，或联系千问平台客服"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"千问API调用未知失败：{str(e)} | 请检查API Key、网络、模型参数等配置"
        logger.error(f"[千问流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)


# ==============================================
# 3. 普通非流式对话（备用接口）
# ==============================================
def chat_completion(chat_entry: ChatEntry, user_message: str):
    """
    千问非流式对话（备用）
    """
    user_id = chat_entry.user.id
    chat_entry_id = chat_entry.id
    logger.info(f"[开始非流式对话请求] 对话ID: {chat_entry_id} | 用户ID: {user_id}")

    try:
        client = get_qwen_client(chat_entry.user)
    except (ValueError, Exception) as e:
        raise Exception(f"客户端初始化失败：{str(e)}")

    messages = [
        {"role": "system", "content": chat_entry.system_prompt}
    ]
    for msg in chat_entry.messages.all():
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    try:
        logger.info(f"[调用千问非流式API] 模型: {DEFAULT_MODEL} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=chat_entry.temperature,
            top_p=chat_entry.top_p,
            max_tokens=chat_entry.max_tokens,
            stream=False
        )
        logger.info(f"[千问非流式API请求成功] 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        return completion.choices[0].message.content

    # 与流式接口保持一致的精准异常捕获
    except AuthenticationError as e:
        error_msg = f"API Key认证失败：{str(e)} | 请检查API Key是否有效（如过期、权限不足）"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except RateLimitError as e:
        error_msg = f"API额度/限流触发：{str(e)} | 请检查千问API额度是否耗尽，或是否触发频率限制"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except APIConnectionError as e:
        error_msg = f"API网络连接失败：{str(e)} | 请检查网络是否正常，或千问API服务是否可用"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except NotFoundError as e:
        error_msg = f"模型/接口不存在：{str(e)} | 当前使用模型 {DEFAULT_MODEL} 可能未开通，请检查模型权限"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except APIError as e:
        error_msg = f"千问API服务异常：{str(e)} | 请稍后重试，或联系千问平台客服"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"千问API调用未知失败：{str(e)} | 请检查API Key、网络、模型参数等配置"
        logger.error(f"[千问非流式API调用失败] {error_msg} | 对话ID: {chat_entry_id} | 用户ID: {user_id}")
        raise Exception(error_msg)