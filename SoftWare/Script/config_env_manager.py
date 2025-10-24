"""
环境变量配置管理器 - 从 config.json 读取环境变量名称，再从系统环境变量读取实际的密钥值

核心思想：
1. config.json 中存储的是环境变量名称（如 "GEMINI_API_KEY"），而不是真实密钥
2. 应用从 config.json 读取环境变量名称
3. 然后从系统环境变量读取对应名称的真实密钥
4. 这样做的好处：
   - 配置文件可以安全提交到版本控制（不含真实密钥）
   - 不同开发者在不同电脑上只需配置本地环境变量
   - 无需修改配置文件就能使用不同的 API 密钥
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

class ConfigEnvManager:
    """
    环境变量配置管理器
    
    从 config.json 读取环境变量名称配置，然后从系统环境变量读取实际值
    """
    
    _instance = None
    _config_cache = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once()
        return cls._instance
    
    def _init_once(self):
        """初始化一次"""
        self.config_file = self._find_config_file()
        self._load_config()
    
    @staticmethod
    def _find_config_file() -> Path:
        """查找 config.json 文件"""
        # 尝试多个位置
        possible_paths = [
            Path(__file__).parent / "config.json",  # 脚本同目录
            Path(__file__).parent.parent / "config.json",  # 上级目录
            Path.cwd() / "config.json",  # 当前工作目录
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"[OK] 找到 config.json: {path}")
                return path
        
        raise FileNotFoundError(f"无法找到 config.json，已搜索位置：{possible_paths}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
                print(f"[OK] 配置文件已加载: {self.config_file}")
        except Exception as e:
            print(f"[ERROR] 加载配置文件失败: {e}")
            self._config_cache = {}
    
    def get_raw_config(self) -> Dict:
        """获取原始配置字典"""
        if self._config_cache is None:
            self._load_config()
        return self._config_cache
    
    def get_env_var_name(self, key_path: str) -> Optional[str]:
        """
        获取某个配置项对应的环境变量名称
        
        Args:
            key_path: 配置路径，用点号分隔（例如 'environment.gemini_api_key_env'）
        
        Returns:
            环境变量名称（例如 'GEMINI_API_KEY'），如果不存在则返回 None
        """
        config = self.get_raw_config()
        
        # 按点号路径递归获取
        keys = key_path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def get_secret_from_env(self, env_var_name: str) -> Optional[str]:
        """
        从系统环境变量读取密钥
        
        Args:
            env_var_name: 环境变量名称（例如 'GEMINI_API_KEY'）
        
        Returns:
            环境变量的值，如果不存在则返回 None
        """
        value = os.getenv(env_var_name)
        
        if value:
            # 打印星号隐藏密钥内容
            masked = '*' * max(1, len(value) - 4) + value[-4:] if len(value) > 4 else '*' * len(value)
            print(f"[OK] 从环境变量 {env_var_name} 读取密钥（值：{masked}）")
        else:
            print(f"[WARNING] 环境变量 {env_var_name} 未设置")
        
        return value
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        获取 API 密钥
        
        Args:
            provider: API 提供商名称（gemini/deepseek/claude/gpt4）
        
        Returns:
            API 密钥，如果不存在则返回 None
        """
        # 从配置文件获取环境变量名称
        env_var_name = self.get_env_var_name(f'api.providers.{provider}.api_key_env')
        
        if not env_var_name:
            print(f"[WARNING] 找不到 {provider} 的环境变量配置")
            return None
        
        # 从系统环境变量获取密钥
        return self.get_secret_from_env(env_var_name)
    
    def get_search_engine_api_key(self, engine: str) -> Optional[str]:
        """
        获取搜索引擎 API 密钥
        
        Args:
            engine: 搜索引擎名称（baidu/google）
        
        Returns:
            API 密钥，如果不存在则返回 None
        """
        env_var_name = self.get_env_var_name(f'search_engine.engines.{engine}.api_key_env')
        
        if not env_var_name:
            print(f"[WARNING] 找不到 {engine} 搜索引擎的环境变量配置")
            return None
        
        return self.get_secret_from_env(env_var_name)
    
    def get_search_engine_id(self, engine: str) -> Optional[str]:
        """
        获取搜索引擎 ID（如 Google 的 search engine ID）
        
        Args:
            engine: 搜索引擎名称
        
        Returns:
            搜索引擎 ID，如果不存在则返回 None
        """
        env_var_name = self.get_env_var_name(f'search_engine.engines.{engine}.engine_id_env')
        
        if not env_var_name:
            return None
        
        return self.get_secret_from_env(env_var_name)
    
    def get_config_value(self, key_path: str) -> Any:
        """
        获取配置文件中的任意值
        
        Args:
            key_path: 配置路径，用点号分隔
        
        Returns:
            配置值
        """
        config = self.get_raw_config()
        
        keys = key_path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def reload_config(self):
        """重新加载配置文件"""
        self._config_cache = None
        self._load_config()


def get_config_env_manager() -> ConfigEnvManager:
    """获取全局配置管理器实例"""
    return ConfigEnvManager()


# 便捷函数
def get_api_key(provider: str) -> Optional[str]:
    """快捷函数：获取 API 密钥"""
    return get_config_env_manager().get_api_key(provider)


def get_search_api_key(engine: str) -> Optional[str]:
    """快捷函数：获取搜索引擎密钥"""
    return get_config_env_manager().get_search_engine_api_key(engine)


def get_search_engine_id(engine: str) -> Optional[str]:
    """快捷函数：获取搜索引擎 ID"""
    return get_config_env_manager().get_search_engine_id(engine)


def get_config(key_path: str) -> Any:
    """快捷函数：获取配置值"""
    return get_config_env_manager().get_config_value(key_path)


if __name__ == '__main__':
    # 测试
    print("=== 环境变量配置管理器测试 ===\n")
    
    manager = get_config_env_manager()
    
    # 测试 API 密钥读取
    print("【API 密钥】")
    providers = ['gemini', 'deepseek', 'claude', 'gpt4']
    for provider in providers:
        key = manager.get_api_key(provider)
        print(f"  {provider}: {'已配置' if key else '未配置'}")
    
    # 测试搜索引擎密钥
    print("\n【搜索引擎密钥】")
    engines = ['baidu', 'google']
    for engine in engines:
        key = manager.get_search_engine_api_key(engine)
        engine_id = manager.get_search_engine_id(engine)
        print(f"  {engine}: API密钥={'已配置' if key else '未配置'}, ID={'已配置' if engine_id else '未配置'}")
    
    # 测试配置读取
    print("\n【其他配置】")
    print(f"  当前 API 提供商: {manager.get_config_value('api.current_provider')}")
    print(f"  主题深色模式: {manager.get_config_value('app.theme.dark_mode_enabled')}")
    
    print("\n[OK] 配置管理器测试完成")
