import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 代理设置 - 用于越过防火墙访问 API
def setup_proxy():
    """设置本机代理，默认端口 7890"""
    proxy_host = "127.0.0.1"
    proxy_port = "7890"
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    
    # 设置环境变量代理
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url
    
    # 使用ASCII字符避免编码问题
    print(f"[OK] Proxy set: {proxy_url}")

# 初始化时自动设置代理
setup_proxy()

# 配置文件路径：位于 SoftWare 目录下，便于打包与分发
_BASE_DIR = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _BASE_DIR / "api_settings.json"

# 默认配置，保持与历史版本一致
_DEFAULT_CONFIG = {
    "current_provider": "deepseek",
    "providers": {
        "deepseek": {
            "api_key": "sk-91c8333c0f754ede8de847fadade03b4",
            "api_url": "https://api.deepseek.com/chat/completions",
            "model": "deepseek-chat",
            "display_name": "DeepSeek"
        },
        "gemini": {
            "api_key": "",  # 将从环境变量 GEMINI_API_KEY 获取
            "api_url": "",  # Gemini 使用 SDK，不需要手动配置 URL
            "model": "gemini-2.5-flash",  # 使用 gemini-2.5-flash 模型
            "display_name": "Gemini"
        }
    },
    # 保持向后兼容性的旧配置字段
    "api_key": "sk-91c8333c0f754ede8de847fadade03b4",
    "api_url": "https://api.deepseek.com/chat/completions",
    "model": "deepseek-chat"
}


def _ensure_config_file_exists() -> None:
    """确保配置文件存在，不存在时创建默认配置。"""
    if not _CONFIG_PATH.exists():
        save_api_config(_DEFAULT_CONFIG)


def load_api_config() -> Dict[str, Any]:
    """加载API配置，如无则创建默认配置。"""
    _ensure_config_file_exists()
    try:
        with _CONFIG_PATH.open('r', encoding='utf-8') as fp:
            data = json.load(fp)
    except (json.JSONDecodeError, OSError):
        data = _DEFAULT_CONFIG.copy()
        save_api_config(data)
        return data

    # 补全缺失字段
    updated = False
    for key, value in _DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = value
            updated = True
    if updated:
        save_api_config(data)
    return data


def save_api_config(config: Dict[str, Any]) -> None:
    """保存配置到磁盘。"""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONFIG_PATH.open('w', encoding='utf-8') as fp:
        json.dump(config, fp, ensure_ascii=False, indent=2)


def update_api_config(*, api_key: Optional[str] = None, api_url: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """更新配置中的字段并写回磁盘，返回最新配置。"""
    config = load_api_config()
    changed = False

    # 确保providers结构存在
    if 'providers' not in config:
        config['providers'] = _DEFAULT_CONFIG['providers'].copy()
        changed = True
    
    if 'current_provider' not in config:
        config['current_provider'] = 'deepseek'
        changed = True

    current_provider = config.get('current_provider', 'deepseek')
    
    # 更新当前提供商的配置
    if api_key is not None:
        if 'providers' in config and current_provider in config['providers']:
            if config['providers'][current_provider].get('api_key') != api_key:
                config['providers'][current_provider]['api_key'] = api_key
                config['api_key'] = api_key  # 向后兼容
                changed = True

    if api_url is not None:
        if 'providers' in config and current_provider in config['providers']:
            if config['providers'][current_provider].get('api_url') != api_url:
                config['providers'][current_provider]['api_url'] = api_url
                config['api_url'] = api_url  # 向后兼容
                changed = True

    if model is not None:
        if 'providers' in config and current_provider in config['providers']:
            if config['providers'][current_provider].get('model') != model:
                config['providers'][current_provider]['model'] = model
                config['model'] = model  # 向后兼容
                changed = True

    # 切换提供商
    if provider is not None and provider != config.get('current_provider'):
        if provider in config.get('providers', {}):
            config['current_provider'] = provider
            # 更新顶层字段以保持向后兼容
            provider_config = config['providers'][provider]
            config['api_key'] = provider_config.get('api_key', '')
            config['api_url'] = provider_config.get('api_url', '')
            config['model'] = provider_config.get('model', '')
            changed = True

    if changed:
        save_api_config(config)
    return config


def mask_sensitive_value(value: str, *, visible_prefix: int = 4, visible_suffix: int = 2, mask_char: str = '*') -> str:
    """将敏感信息掩码，保留开头与结尾部分字符。"""
    if not value:
        return ""

    length = len(value)
    if length <= 2:
        return mask_char * length

    if length <= visible_prefix:
        return value[0] + mask_char * (length - 1)

    suffix_len = min(visible_suffix, max(0, length - visible_prefix))
    prefix = value[:visible_prefix]
    suffix = value[-suffix_len:] if suffix_len else ""
    masked_len = length - len(prefix) - len(suffix)
    if masked_len <= 0:
        masked_len = max(1, length - len(prefix))
        suffix = value[-1:] if length - len(prefix) >= 1 else ""
    masked_middle = mask_char * masked_len
    return prefix + masked_middle + suffix


def get_masked_config() -> Dict[str, str]:
    """获取掩码后的配置，用于UI显示。"""
    config = load_api_config()
    return {
        'api_key': mask_sensitive_value(config.get('api_key', '')),
        'api_url': mask_sensitive_value(config.get('api_url', '')),
        'model': config.get('model', '')
    }


def get_current_provider_config() -> Dict[str, Any]:
    """获取当前提供商的完整配置。"""
    config = load_api_config()
    current_provider = config.get('current_provider', 'deepseek')
    providers = config.get('providers', _DEFAULT_CONFIG['providers'])
    
    if current_provider in providers:
        provider_config = providers[current_provider].copy()
        return provider_config
    
    # 如果当前提供商不存在，返回deepseek作为默认
    return providers.get('deepseek', _DEFAULT_CONFIG['providers']['deepseek']).copy()


def get_available_providers() -> Dict[str, Dict[str, str]]:
    """获取所有可用的API提供商列表。"""
    config = load_api_config()
    return config.get('providers', _DEFAULT_CONFIG['providers'])


def get_current_provider_name() -> str:
    """获取当前提供商名称。"""
    config = load_api_config()
    return config.get('current_provider', 'deepseek')


def switch_provider(provider_name: str) -> bool:
    """切换到指定的API提供商。"""
    config = load_api_config()
    providers = config.get('providers', _DEFAULT_CONFIG['providers'])
    
    if provider_name not in providers:
        return False
        
    update_api_config(provider=provider_name)
    return True


def set_gemini_api_key(api_key: str) -> bool:
    """设置 Gemini API 密钥，同时更新配置文件、进程环境变量和系统环境变量。"""
    import os
    import platform
    
    try:
        # 1. 设置当前进程环境变量
        os.environ['GEMINI_API_KEY'] = api_key
        print(f"[OK] 已设置进程环境变量 GEMINI_API_KEY")
        
        # 2. 保存到配置文件
        update_api_config(api_key=api_key)
        print(f"[OK] 已保存到配置文件")
        
        # 3. 设置系统环境变量（Windows）
        if platform.system() == 'Windows':
            try:
                import winreg
                # 打开用户环境变量注册表
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, 'GEMINI_API_KEY', 0, winreg.REG_SZ, api_key)
                winreg.CloseKey(key)
                print(f"[OK] 已设置Windows系统环境变量 GEMINI_API_KEY")
                
                # 广播环境变量更改消息
                import ctypes
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x001A
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', 
                    2, 1000, None
                )
                print(f"[OK] 已广播环境变量更改")
            except Exception as e:
                print(f"[WARNING] 设置Windows系统环境变量失败: {e}")
                print(f"[WARNING] 但进程环境变量已设置，程序可以正常使用")
        
        return True
    except Exception as e:
        print(f"[ERROR] 设置 Gemini API 密钥失败: {e}")
        return False


def get_gemini_api_key() -> str:
    """获取 Gemini API 密钥，优先从环境变量获取。"""
    import os
    
    # 优先从环境变量获取
    env_key = os.getenv('GEMINI_API_KEY')
    if env_key:
        return env_key
    
    # 从配置文件获取
    config = load_api_config()
    providers = config.get('providers', {})
    gemini_config = providers.get('gemini', {})
    return gemini_config.get('api_key', '')


def update_gemini_model_to_2_5():
    """更新 Gemini 模型为 2.5-flash"""
    config = load_api_config()
    if 'gemini' in config:
        config['gemini']['model'] = 'gemini-2.5-flash'
        save_api_config(config)
        print("[OK] Gemini 模型已更新为 gemini-2.5-flash")
    else:
        print("[ERROR] 未找到 Gemini 配置")

