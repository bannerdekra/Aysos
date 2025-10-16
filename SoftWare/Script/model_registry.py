"""
AI模型统一配置中心
管理所有AI模型的名称、API Key逻辑、基础URL和上下文限制
便于未来快速添加Claude、GPT-4o等模型
"""
import os
from typing import Dict, Optional, Tuple


class ModelConfig:
    """单个模型的配置"""
    def __init__(
        self,
        name: str,
        display_name: str,
        api_url: str,
        default_model: str,
        context_limit: int,
        env_key_name: Optional[str] = None,
        requires_proxy: bool = False,
        supports_files: bool = False,
        supports_vision: bool = False,
        supports_video: bool = False
    ):
        self.name = name  # 内部标识名
        self.display_name = display_name  # 显示名称
        self.api_url = api_url  # API基础URL
        self.default_model = default_model  # 默认模型名
        self.context_limit = context_limit  # 上下文token限制
        self.env_key_name = env_key_name  # 环境变量名
        self.requires_proxy = requires_proxy  # 是否需要代理
        self.supports_files = supports_files  # 是否支持文件上传
        self.supports_vision = supports_vision  # 是否支持图片理解
        self.supports_video = supports_video  # 是否支持视频理解
    
    def get_api_key(self) -> Optional[str]:
        """从环境变量获取API Key"""
        if self.env_key_name:
            return os.getenv(self.env_key_name)
        return None
    
    def validate_config(self) -> Tuple[bool, str]:
        """验证配置是否完整"""
        if self.env_key_name:
            api_key = self.get_api_key()
            if not api_key:
                return False, f"环境变量 {self.env_key_name} 未设置"
        
        if not self.api_url:
            return False, "API URL 未配置"
        
        return True, "配置完整"


class ModelRegistry:
    """模型注册表 - 统一管理所有AI模型"""
    
    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._register_default_models()
    
    def _register_default_models(self):
        """注册默认模型"""
        
        # DeepSeek
        self.register_model(ModelConfig(
            name="deepseek",
            display_name="DeepSeek",
            api_url="https://api.deepseek.com/v1/chat/completions",
            default_model="deepseek-chat",
            context_limit=32000,
            env_key_name="DeepSeek-APIKEY",
            requires_proxy=False,
            supports_files=False,
            supports_vision=False,
            supports_video=False
        ))
        
        # Gemini
        self.register_model(ModelConfig(
            name="gemini",
            display_name="Google Gemini",
            api_url="https://generativelanguage.googleapis.com/v1beta",
            default_model="gemini-2.0-flash-exp",
            context_limit=1000000,  # 1M tokens
            env_key_name="GEMINI_API_KEY",
            requires_proxy=True,
            supports_files=True,
            supports_vision=True,
            supports_video=True
        ))
        
        # Claude (预留，待实现)
        self.register_model(ModelConfig(
            name="claude",
            display_name="Anthropic Claude",
            api_url="https://api.anthropic.com/v1/messages",
            default_model="claude-3-5-sonnet-20241022",
            context_limit=200000,
            env_key_name="CLAUDE_API_KEY",
            requires_proxy=False,
            supports_files=True,
            supports_vision=True,
            supports_video=False
        ))
        
        # GPT-4o (预留，待实现)
        self.register_model(ModelConfig(
            name="gpt4o",
            display_name="OpenAI GPT-4o",
            api_url="https://api.openai.com/v1/chat/completions",
            default_model="gpt-4o",
            context_limit=128000,
            env_key_name="OPENAI_API_KEY",
            requires_proxy=False,
            supports_files=False,
            supports_vision=True,
            supports_video=False
        ))
    
    def register_model(self, config: ModelConfig):
        """注册新模型"""
        self._models[config.name] = config
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self._models.get(name)
    
    def get_all_models(self) -> Dict[str, ModelConfig]:
        """获取所有模型"""
        return self._models.copy()
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """获取所有配置完整的模型"""
        available = {}
        for name, config in self._models.items():
            is_valid, _ = config.validate_config()
            if is_valid:
                available[name] = config
        return available
    
    def list_model_names(self) -> list:
        """列出所有模型名称"""
        return list(self._models.keys())
    
    def list_available_model_names(self) -> list:
        """列出所有可用模型名称"""
        return list(self.get_available_models().keys())


# 全局单例
_registry = None


def get_model_registry() -> ModelRegistry:
    """获取模型注册表单例"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """快捷方法：获取模型配置"""
    registry = get_model_registry()
    return registry.get_model(model_name)


def validate_model(model_name: str) -> Tuple[bool, str]:
    """快捷方法：验证模型配置"""
    config = get_model_config(model_name)
    if not config:
        return False, f"模型 {model_name} 未注册"
    return config.validate_config()


# 使用示例
if __name__ == "__main__":
    registry = get_model_registry()
    
    print("=" * 50)
    print("所有已注册模型:")
    print("=" * 50)
    for name, config in registry.get_all_models().items():
        print(f"\n【{config.display_name}】")
        print(f"  内部名称: {config.name}")
        print(f"  默认模型: {config.default_model}")
        print(f"  API URL: {config.api_url}")
        print(f"  上下文限制: {config.context_limit:,} tokens")
        print(f"  环境变量: {config.env_key_name or '无'}")
        print(f"  需要代理: {'是' if config.requires_proxy else '否'}")
        print(f"  支持文件: {'是' if config.supports_files else '否'}")
        print(f"  支持图片: {'是' if config.supports_vision else '否'}")
        print(f"  支持视频: {'是' if config.supports_video else '否'}")
        
        is_valid, message = config.validate_config()
        print(f"  配置状态: {'✅ ' + message if is_valid else '❌ ' + message}")
    
    print("\n" + "=" * 50)
    print("可用模型列表:")
    print("=" * 50)
    available = registry.get_available_models()
    if available:
        for name in available.keys():
            print(f"  ✓ {available[name].display_name}")
    else:
        print("  (无可用模型，请配置环境变量)")
