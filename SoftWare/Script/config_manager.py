#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理模块 - config_manager.py

提供一个集中式的配置管理接口，所有脚本通过此模块访问和修改配置。
支持自动持久化、默认值合并、多模块间的配置共享。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import threading

class ConfigManager:
    """统一配置管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式确保全局只有一个配置实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        self._config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        self._config = {}
        self._default_config = self._get_default_config()
        self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "_version": "1.0.0",
            "_description": "Unified configuration file for Agent Chat Application",
            "_last_updated": "2025-10-20",
            
            "app": {
                "name": "Agent Chat",
                "version": "1.0.9",
                "theme": {
                    "dark_mode_enabled": False,
                    "auto_dark_mode": False,
                    "custom_background_path": "",
                    "is_video_background": False
                },
                "ui": {
                    "collapse_threshold": 300,
                    "preview_length": 100,
                    "user_bubble_collapse_threshold": 300,
                    "user_and_agent_preview_length": 100
                }
            },
            
            "storage": {
                "type": "file",
                "file_storage": {
                    "base_path": "C:\\AgentData",
                    "auto_create_folder": True,
                    "folder_name": "AgentData",
                    "conversation_subfolder": "conversations"
                },
                "last_migration": None
            },
            
            "api": {
                "current_provider": "gemini",
                "default_model": "gemini-2.5-flash",
                "providers": {
                    "gemini": {
                        "api_key": "",
                        "api_url": "",
                        "model": "gemini-2.5-flash",
                        "display_name": "Gemini"
                    },
                    "deepseek": {
                        "api_key": "",
                        "api_url": "https://api.deepseek.com/v1",
                        "model": "deepseek-chat",
                        "display_name": "DeepSeek"
                    },
                    "claude": {
                        "api_key": "",
                        "api_url": "",
                        "model": "claude-3-sonnet",
                        "display_name": "Claude"
                    },
                    "gpt4": {
                        "api_key": "",
                        "api_url": "https://api.openai.com/v1",
                        "model": "gpt-4-turbo",
                        "display_name": "GPT-4"
                    }
                }
            },
            
            "search_engine": {
                "enabled_engines": ["baidu"],
                "primary_engine": "baidu",
                "fallback_enabled": False,
                "selection_order": ["baidu"]
            },
            
            "sd_diffusion": {
                "sampler_name": "DPM++ 2S a",
                "scheduler": "Karras",
                "steps": 50,
                "cfg_scale": 8.0,
                "seed": -1,
                "width": 512,
                "height": 512,
                "model": "sd1.5\\sd_xl_base_1.0_0.9vae.safetensors",
                "prompt": "",
                "negative_prompt": "lowres, bad quality, deformed, blurry, worst quality"
            }
        }
    
    def _load_config(self):
        """从文件加载配置，如果不存在则使用默认配置"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # 合并配置：用文件中的配置覆盖默认配置
                self._config = self._merge_config(self._default_config, loaded_config)
            else:
                self._config = self._default_config.copy()
                self._save_config()
        except Exception as e:
            print(f"[CONFIG] 加载配置文件失败: {e}，使用默认配置")
            self._config = self._default_config.copy()
    
    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """递归合并配置字典"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            print(f"[CONFIG] 配置已保存到 {self._config_file}")
        except Exception as e:
            print(f"[CONFIG] 保存配置文件失败: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置路径，支持点号分隔（例：'app.theme.dark_mode_enabled'）
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any, auto_save: bool = True):
        """
        设置配置值
        
        Args:
            key_path: 配置路径，支持点号分隔
            value: 要设置的值
            auto_save: 是否自动保存
        """
        keys = key_path.split('.')
        config = self._config
        
        # 递归创建嵌套字典
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        
        if auto_save:
            self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def reset_to_default(self):
        """重置为默认配置"""
        self._config = self._default_config.copy()
        self._save_config()
    
    def reload(self):
        """重新加载配置（从文件）"""
        self._load_config()


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便捷函数 - 快速访问配置
def config_get(key_path: str, default: Any = None) -> Any:
    """快捷获取配置"""
    return get_config_manager().get(key_path, default)


def config_set(key_path: str, value: Any, auto_save: bool = True):
    """快捷设置配置"""
    get_config_manager().set(key_path, value, auto_save)


def config_get_all() -> Dict[str, Any]:
    """快捷获取所有配置"""
    return get_config_manager().get_all()


def config_reload():
    """快捷重新加载配置"""
    get_config_manager().reload()


# 导出全局实例别名（为了兼容旧代码: from config_manager import config_manager）
config_manager = get_config_manager()
