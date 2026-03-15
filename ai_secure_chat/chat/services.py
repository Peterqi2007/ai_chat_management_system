"""
大模型 API 服务层
功能：Minimax 流式响应、参数配置、异常处理、日志记录
适配：OpenAI SDK v1.0+ / Django/Mezzanine
"""
import logging
from typing import Generator, List, Dict
from django.conf import settings
from openai import OpenAI, APIError, ConnectionError, Timeout

# 配置日志（复用 Django 日志）
logger = logging.getLogger(__name__)

# 初始化 OpenAI 客户端（适配 Minimax 兼容接口）
client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    # 超时设置，避免请求阻塞
    timeout=60.0
)

def minimax_stream_chat(
    messages: List[Dict[str, str]],
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None
) -> Generator[str, None, None]:
    """
    Minimax 流式对话接口
    :param messages: 对话历史 [{"role": "user"/"assistant", "content": "xxx"}, ...]
    :param temperature: 温度系数 (0-1)，值越高越随机，越低越精准
    :param max_tokens: 最大生成 token 数
    :param top_p: 核采样参数
    :return: 流式生成器 (yield 字符串片段)
    """
    # 优先级：传入参数 > settings 默认参数
    temperature = temperature or settings.LLM_DEFAULT_TEMPERATURE
    max_tokens = max_tokens or settings.LLM_DEFAULT_MAX_TOKENS
    top_p = top_p or settings.LLM_DEFAULT_TOP_P

    try:
        # 调用 Minimax 流式接口（核心：stream=True）
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            stream=True,  # 开启流式响应
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=settings.LLM_DEFAULT_FREQUENCY_PENALTY,
            presence_penalty=settings.LLM_DEFAULT_PRESENCE_PENALTY,
            # Minimax 专属可选参数（如需可开启）
            # stop=["\n\n\n"],
        )

        # 迭代流式返回的 chunk
        for chunk in response:
            # 获取 AI 回复的文本片段
            content = chunk.choices[0].delta.content
            if content:
                # 日志记录流式片段（可选）
                # logger.debug(f"流式输出片段: {content}")
                yield content

    # 异常处理（前端友好提示）
    except APIError as e:
        error_msg = f"Minimax API 错误: {e.message} (code: {e.status_code})"
        logger.error(error_msg)
        yield f"[错误] {error_msg}"
    except ConnectionError:
        error_msg = "网络连接失败，请检查网络后重试"
        logger.error(error_msg)
        yield f"[错误] {error_msg}"
    except Timeout:
        error_msg = "请求超时，Minimax 服务器响应缓慢"
        logger.error(error_msg)
        yield f"[错误] {error_msg}"
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        logger.error(error_msg)
        yield f"[错误] {error_msg}"