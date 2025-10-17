"""
搜索引擎配置管理器
管理用户的搜索引擎选择和优先级配置
"""
import os
import json
from typing import List, Dict, Any, Optional


class SearchEngineConfig:
    """搜索引擎配置管理类"""
    
    CONFIG_FILE = "search_engine_config.json"
    
    # 可用的搜索引擎
    AVAILABLE_ENGINES = {
        "baidu": {
            "name": "百度搜索",
            "description": "适合中文内容和国内信息",
            "icon": "🔵",
            "requires_proxy": False
        },
        "google": {
            "name": "Google搜索",
            "description": "适合英文内容和国际信息",
            "icon": "🔴",
            "requires_proxy": True
        }
    }
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_path = os.path.join(
            os.path.dirname(__file__),
            self.CONFIG_FILE
        )
        self.config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled_engines": ["baidu", "google"],  # 启用的搜索引擎
            "primary_engine": "baidu",               # 优先使用的引擎
            "fallback_enabled": True,                # 是否启用备用引擎
            "selection_order": ["baidu", "google"]   # 用户选择顺序（记录先选谁）
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[搜索引擎配置] ✅ 已加载配置: {config}")
                    return config
            except Exception as e:
                print(f"[搜索引擎配置] ⚠️ 加载失败: {e}，使用默认配置")
        
        # 返回默认配置
        return self._get_default_config()
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"[搜索引擎配置] 💾 配置已保存")
        except Exception as e:
            print(f"[搜索引擎配置] ❌ 保存失败: {e}")
    
    def get_enabled_engines(self) -> List[str]:
        """获取启用的搜索引擎列表"""
        return self.config.get("enabled_engines", ["baidu"])
    
    def get_primary_engine(self) -> str:
        """获取优先使用的搜索引擎"""
        return self.config.get("primary_engine", "baidu")
    
    def is_fallback_enabled(self) -> bool:
        """是否启用备用引擎"""
        return self.config.get("fallback_enabled", True)
    
    def get_selection_order(self) -> List[str]:
        """获取用户选择顺序"""
        return self.config.get("selection_order", ["baidu"])
    
    def set_engines(self, engines: List[str], primary: Optional[str] = None):
        """
        设置启用的搜索引擎
        
        Args:
            engines: 启用的引擎列表
            primary: 优先引擎（如果不指定，使用列表第一个）
        """
        # 验证引擎名称
        valid_engines = [e for e in engines if e in self.AVAILABLE_ENGINES]
        
        if not valid_engines:
            print("[搜索引擎配置] ⚠️ 没有有效的搜索引擎")
            return
        
        # 更新配置
        self.config["enabled_engines"] = valid_engines
        
        # 设置优先引擎
        if primary and primary in valid_engines:
            self.config["primary_engine"] = primary
        else:
            self.config["primary_engine"] = valid_engines[0]
        
        # 记录选择顺序
        self.config["selection_order"] = valid_engines.copy()
        
        # 是否启用备用
        self.config["fallback_enabled"] = len(valid_engines) > 1
        
        # 保存配置
        self._save_config()
        
        print(f"[搜索引擎配置] ✅ 已更新: 启用 {valid_engines}, 优先 {self.config['primary_engine']}")
    
    def toggle_engine(self, engine: str):
        """
        切换搜索引擎的启用状态
        
        Args:
            engine: 引擎名称
        """
        if engine not in self.AVAILABLE_ENGINES:
            print(f"[搜索引擎配置] ⚠️ 未知引擎: {engine}")
            return
        
        enabled = self.config["enabled_engines"]
        selection_order = self.config["selection_order"]
        
        if engine in enabled:
            # 已启用，禁用它
            if len(enabled) <= 1:
                print(f"[搜索引擎配置] ⚠️ 至少需要启用一个搜索引擎")
                return
            
            enabled.remove(engine)
            if engine in selection_order:
                selection_order.remove(engine)
            
            # 如果禁用的是优先引擎，切换到第一个启用的
            if self.config["primary_engine"] == engine:
                self.config["primary_engine"] = enabled[0]
        else:
            # 未启用，启用它
            enabled.append(engine)
            # 添加到选择顺序末尾
            if engine not in selection_order:
                selection_order.append(engine)
        
        # 更新备用引擎状态
        self.config["fallback_enabled"] = len(enabled) > 1
        
        # 保存配置
        self._save_config()
        
        print(f"[搜索引擎配置] ✅ 已切换 {engine}: {'启用' if engine in enabled else '禁用'}")
    
    def set_primary_engine(self, engine: str):
        """
        设置优先使用的搜索引擎
        
        Args:
            engine: 引擎名称
        """
        if engine not in self.config["enabled_engines"]:
            print(f"[搜索引擎配置] ⚠️ 引擎 {engine} 未启用")
            return
        
        # 更新优先引擎
        old_primary = self.config["primary_engine"]
        self.config["primary_engine"] = engine
        
        # 更新选择顺序（将新的优先引擎移到前面）
        selection_order = self.config["selection_order"]
        if engine in selection_order:
            selection_order.remove(engine)
        selection_order.insert(0, engine)
        
        # 保存配置
        self._save_config()
        
        print(f"[搜索引擎配置] ✅ 优先引擎: {old_primary} → {engine}")
    
    def get_engine_info(self, engine: str) -> Dict[str, Any]:
        """获取引擎信息"""
        return self.AVAILABLE_ENGINES.get(engine, {})
    
    def get_config_summary(self) -> str:
        """获取配置摘要"""
        enabled = self.get_enabled_engines()
        primary = self.get_primary_engine()
        
        summary_lines = [
            "🔍 搜索引擎配置:",
            f"  启用: {', '.join(enabled)}",
            f"  优先: {primary}",
            f"  备用: {'是' if self.is_fallback_enabled() else '否'}"
        ]
        
        return "\n".join(summary_lines)


# 全局单例
_search_engine_config = None


def get_search_engine_config() -> SearchEngineConfig:
    """获取搜索引擎配置管理器的全局实例"""
    global _search_engine_config
    if _search_engine_config is None:
        _search_engine_config = SearchEngineConfig()
    return _search_engine_config


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("搜索引擎配置管理器测试")
    print("=" * 60)
    
    config = SearchEngineConfig()
    
    # 显示当前配置
    print("\n当前配置:")
    print(config.get_config_summary())
    
    # 测试切换引擎
    print("\n测试切换 Google:")
    config.toggle_engine("google")
    print(config.get_config_summary())
    
    # 测试设置优先引擎
    print("\n测试设置 Google 为优先:")
    config.set_primary_engine("google")
    print(config.get_config_summary())
    
    # 测试重新启用百度
    print("\n测试重新启用百度:")
    config.toggle_engine("baidu")
    print(config.get_config_summary())
