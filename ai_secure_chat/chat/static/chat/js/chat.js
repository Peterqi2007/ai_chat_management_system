// chat/static/chat/js/chat.js
// 大模型对话系统 - 流式响应前端逻辑
document.addEventListener('DOMContentLoaded', function () {
    // 发送消息函数
    window.sendMessage = function () {
        const userInput = document.getElementById('user_input');
        const replyArea = document.getElementById('reply_area');
        const convId = document.getElementById('conv_id').value;
        const message = userInput.value.trim();

        if (!message) return;

        // 清空输入框
        userInput.value = '';
        // 初始化回复区
        replyArea.textContent = 'AI 思考中...';

        // 创建流式请求
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/chat/stream/', true);
        xhr.responseType = 'text';

        // 实时接收流式数据（打字机效果）
        xhr.onprogress = function () {
            replyArea.textContent = xhr.response;
        };

        // 请求完成回调
        xhr.onload = function () {
            if (xhr.status !== 200) {
                replyArea.textContent = '[错误] 对话请求失败，请重试';
            }
        };

        // 构造表单数据
        const formData = new FormData();
        formData.append('conversation_id', convId);
        formData.append('content', message);

        xhr.send(formData);
    };
});