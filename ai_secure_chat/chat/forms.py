from django import forms
from django.contrib.auth.models import User
from .models import (
    Category, Folder, ChatEntry, UserProfile, ModelConfig
)

import bcrypt
import hashlib


# ==============================================
# 1. 分类(Category)表单
# 用于分类的新增/编辑
# ==============================================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'order']
        labels = {
            'name': Category._meta.get_field('name').verbose_name,
            'order': Category._meta.get_field('order').verbose_name,
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入分类名称'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


# ==============================================
# 2. 文件夹(Folder)表单
# 用于文件夹的新增/编辑，支持分类和父文件夹关联
# ==============================================
class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name', 'order', 'category', 'parent_folder']
        labels = {
            'name': Folder._meta.get_field('name').verbose_name,
            'order': Folder._meta.get_field('order').verbose_name,
            'category': Folder._meta.get_field('category').verbose_name,
            'parent_folder': Folder._meta.get_field('parent_folder').verbose_name,
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入文件夹名称'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),  """奇怪的order输入"""
            'category': forms.Select(attrs={'class': 'form-select'}),
            'parent_folder': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # 初始化时过滤当前用户的分类和文件夹（需在视图中传入user参数）
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # 分类仅显示当前用户的
            self.fields['category'].queryset = Category.objects.filter(user=self.user)
            # 父文件夹仅显示当前用户的
            self.fields['parent_folder'].queryset = Folder.objects.filter(user=self.user)
            # 空值处理
            self.fields['category'].empty_label = "无分类"
            self.fields['parent_folder'].empty_label = "无父文件夹"


# ==============================================
# 3. 对话条目(ChatEntry)表单
# 用于对话条目的新增/编辑，包含模型参数配置
# ==============================================
class ChatEntryForm(forms.ModelForm):
    class Meta:
        model = ChatEntry
        fields = ['title', 'temperature', 'top_p', 'max_tokens', 'is_private', 'folder']
        labels = {
            'title': ChatEntry._meta.get_field('title').verbose_name,
            'temperature': ChatEntry._meta.get_field('temperature').verbose_name,
            'top_p': ChatEntry._meta.get_field('top_p').verbose_name,
            'max_tokens': ChatEntry._meta.get_field('max_tokens').verbose_name,
            'is_private': ChatEntry._meta.get_field('is_private').verbose_name,
            'folder': ChatEntry._meta.get_field('folder').verbose_name,
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入对话标题'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.0, 'max': 1.0, 'step': 0.01}),
            'top_p': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.0, 'max': 1.0, 'step': 0.01}), #无法理解的键
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8192}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'folder': forms.Select(attrs={'class': 'form-select'}),
        }


    def __init__(self, *args, **kwargs):
        # 初始化时过滤当前用户的文件夹
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['folder'].queryset = Folder.objects.filter(user=self.user)
            self.fields['folder'].empty_label = "请选择所属文件夹"


# ==============================================
# 4. 隐私对话密码验证表单
# 用于访问隐私对话时验证密码（明文输入，后端验证哈希）
# ==============================================
class PrivacyPasswordVerifyForm(forms.Form):
    privacy_password = forms.CharField(
        label="隐私密码",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请输入隐私对话密码'}),
        min_length=6,
        error_messages={
            'required': '请输入隐私密码',
            'min_length': '密码长度不能少于6位'
        }
    )


# ==============================================
# 5. 用户资料(UserProfile)表单
# 用于管理用户扩展资料，包含隐私密码设置（自动哈希存储）
# ==============================================
class UserProfileForm(forms.ModelForm):
    # 新增明文隐私密码字段（模型中存储哈希，表单中输入明文）
    privacy_password = forms.CharField(
        label="隐私密码",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '设置隐私对话密码（不少于6位）'}),
        required=False,
        min_length=6,
        error_messages={
            'min_length': '密码长度不能少于6位'
        }
    )
    # 确认隐私密码（用于设置时验证）
    privacy_password_confirm = forms.CharField(
        label="确认隐私密码",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '再次输入隐私密码'}),
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['default_model', 'api_key']
        labels = {
            'default_model': UserProfile._meta.get_field('default_model').verbose_name,
            'api_key': UserProfile._meta.get_field('api_key').verbose_name,
        }
        widgets = {
            'default_model': forms.Select(attrs={'class': 'form-select'},
                                          choices=[('minimax', 'minimax'), ('gpt-3.5-turbo', 'GPT-3.5'),
                                                   ('gpt-4', 'GPT-4')]),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入API密钥'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('privacy_password')
        password_confirm = cleaned_data.get('privacy_password_confirm')

        # 如果输入了密码但两次不一致，抛出错误
        if password or password_confirm:
            if password != password_confirm:
                self.add_error('privacy_password_confirm', '两次输入的密码不一致')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # 如果输入了新密码，生成哈希并存储
        password = self.cleaned_data.get('privacy_password')
        if password:
            try:
                # bcrypt 哈希加密
                instance.privacy_password_hash = bcrypt.hashpw(
                    password.encode('utf-8'),
                    bcrypt.gensalt()
                ).decode('utf-8')

            except:
                print("bcrypt哈希加密失败") # 上服务器的时候把这句删了
                # 使用sha256哈希（可根据需求替换为更安全的方式，如bcrypt）
                instance.privacy_password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        if commit:
            instance.save()
        return instance


# ==============================================
# 6. 模型参数配置(ModelConfig)表单
# 用于管理全局/自定义模型参数模板
# ==============================================
"""不知道什么用处"""
class ModelConfigForm(forms.ModelForm):
    class Meta:
        model = ModelConfig
        fields = ['name', 'model_name', 'temperature', 'top_p', 'max_tokens', 'is_global']
        labels = {
            'name': ModelConfig._meta.get_field('name').verbose_name,
            'model_name': ModelConfig._meta.get_field('model_name').verbose_name,
            'temperature': ModelConfig._meta.get_field('temperature').verbose_name,
            'top_p': ModelConfig._meta.get_field('top_p').verbose_name,
            'max_tokens': ModelConfig._meta.get_field('max_tokens').verbose_name,
            'is_global': ModelConfig._meta.get_field('is_global').verbose_name,
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入配置名称'}),
            'model_name': forms.Select(attrs={'class': 'form-select'},
                                       choices=[('minimax', 'minimax'), ('gpt-3.5-turbo', 'GPT-3.5'),
                                                ('gpt-4', 'GPT-4')]),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.0, 'max': 1.0, 'step': 0.01}),
            'top_p': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.0, 'max': 1.0, 'step': 0.01}),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8192}),
            'is_global': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
