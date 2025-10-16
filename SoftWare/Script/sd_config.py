"""
Stable Diffusion 创作参数持久化配置
保存用户在创作面板中调整的参数，启动时自动加载
确保用户创作环境和习惯保持一致
"""
import json
import os
from typing import Dict, Optional


class SDConfig:
    """SD参数配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "sampler_name": "DPM++ 2M",
        "scheduler": "Karras",
        "steps": 20,
        "cfg_scale": 7.0,
        "seed": -1,
        "width": 512,
        "height": 512,
        "model": "",  # 空字符串表示使用SD WebUI当前模型
        "prompt": "",
        "negative_prompt": "lowres, bad quality, deformed, blurry, worst quality"
    }
    
    def __init__(self, config_file: str = "sd_config.json"):
        """
        初始化SD配置管理器
        
        Args:
            config_file: 配置文件名（保存在Script目录）
        """
        # 获取Script目录路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(script_dir, config_file)
        
        # 当前配置
        self._config = self.DEFAULT_CONFIG.copy()
        
        # 尝试加载已保存的配置
        self.load()
    
    def load(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            bool: 是否成功加载
        """
        if not os.path.exists(self.config_path):
            print(f"[SD Config] 配置文件不存在，使用默认配置: {self.config_path}")
            return False
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # 合并配置（保留默认值，只更新存在的键）
            for key in self.DEFAULT_CONFIG.keys():
                if key in loaded_config:
                    self._config[key] = loaded_config[key]
            
            print(f"[SD Config] ✅ 成功加载配置: {self.config_path}")
            print(f"[SD Config] 参数: 步数={self._config['steps']}, CFG={self._config['cfg_scale']}, 模型={self._config['model'] or '默认'}")
            return True
            
        except Exception as e:
            print(f"[SD Config] ⚠️ 加载配置失败: {e}")
            return False
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 是否成功保存
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            
            print(f"[SD Config] ✅ 成功保存配置: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"[SD Config] ⚠️ 保存配置失败: {e}")
            return False
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置项"""
        if key in self.DEFAULT_CONFIG:
            self._config[key] = value
        else:
            print(f"[SD Config] ⚠️ 未知配置项: {key}")
    
    def update(self, params: Dict):
        """
        批量更新配置
        
        Args:
            params: 参数字典
        """
        for key, value in params.items():
            if key in self.DEFAULT_CONFIG:
                self._config[key] = value
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
    
    def reset_to_default(self):
        """重置为默认配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        print("[SD Config] 已重置为默认配置")
    
    def get_generation_params(self) -> Dict:
        """
        获取生成参数（排除prompt和negative_prompt）
        
        Returns:
            Dict: 生成参数字典
        """
        params = self._config.copy()
        # 移除提示词（这些应该由用户每次输入）
        params.pop('prompt', None)
        params.pop('negative_prompt', None)
        return params


# 全局单例
_sd_config = None


def get_sd_config() -> SDConfig:
    """获取SD配置管理器单例"""
    global _sd_config
    if _sd_config is None:
        _sd_config = SDConfig()
    return _sd_config


def save_sd_params(params: Dict):
    """
    快捷方法：保存SD参数
    
    Args:
        params: 参数字典
    """
    config = get_sd_config()
    config.update(params)
    config.save()


def load_sd_params() -> Dict:
    """
    快捷方法：加载SD参数
    
    Returns:
        Dict: 参数字典
    """
    config = get_sd_config()
    return config.get_all()


# 使用示例
if __name__ == "__main__":
    print("=" * 50)
    print("SD 配置管理器测试")
    print("=" * 50)
    
    # 创建配置管理器
    config = SDConfig("test_sd_config.json")
    
    # 显示当前配置
    print("\n当前配置:")
    for key, value in config.get_all().items():
        print(f"  {key}: {value}")
    
    # 修改配置
    print("\n修改配置...")
    config.set("steps", 30)
    config.set("cfg_scale", 8.5)
    config.set("model", "stable-diffusion-xl-base-1.0")
    
    # 保存配置
    config.save()
    
    # 重新加载
    print("\n重新加载配置...")
    config2 = SDConfig("test_sd_config.json")
    
    print("\n加载后的配置:")
    for key, value in config2.get_all().items():
        print(f"  {key}: {value}")
    
    # 清理测试文件
    import os
    try:
        os.remove("test_sd_config.json")
        print("\n✅ 测试完成，已清理测试文件")
    except:
        pass
