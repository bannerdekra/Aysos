"""
通用工具执行器
负责注册、管理和执行所有 Function Calling 工具
支持动态工具调用和结果序列化
"""
import json
from typing import Dict, Any, List, Callable, Optional


class ToolExecutor:
    """工具执行器 - 管理和执行所有可用工具"""
    
    def __init__(self):
        """初始化工具执行器"""
        self._tools: Dict[str, Callable] = {}
        self._tool_schemas: List[Dict] = []
        self._tool_descriptions: Dict[str, str] = {}
        
        print("[工具执行器] 初始化...")
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具（根据配置动态注册搜索引擎）"""
        # 获取搜索引擎配置
        try:
            from search_engine_config import get_search_engine_config
            search_config = get_search_engine_config()
            enabled_engines = search_config.get_enabled_engines()
            primary_engine = search_config.get_primary_engine()
            
            print(f"[工具执行器] 搜索引擎配置: 启用 {enabled_engines}, 优先 {primary_engine}")
            
        except Exception as e:
            print(f"[工具执行器] 加载搜索引擎配置失败: {e}，使用默认配置")
            enabled_engines = ["baidu", "google"]
            primary_engine = "baidu"
        
        # 按优先级顺序注册搜索工具
        # 先注册优先引擎，这样在工具列表中会排在前面
        engines_to_register = []
        if primary_engine in enabled_engines:
            engines_to_register.append(primary_engine)
        
        # 添加其他启用的引擎
        for engine in enabled_engines:
            if engine not in engines_to_register:
                engines_to_register.append(engine)
        
        # 注册百度搜索工具
        if "baidu" in engines_to_register:
            try:
                from baidu_searcher import get_baidu_searcher
                
                searcher = get_baidu_searcher()
                priority_tag = " [优先]" if primary_engine == "baidu" else ""
                self.register_tool(
                    name="baidu_search",
                    function=searcher.search,
                    schema=searcher.get_tool_schema(),
                    description=f"百度搜索 - 获取实时网络信息（中文内容优先）{priority_tag}"
                )
                print(f"[工具执行器] 已注册: baidu_search{priority_tag}")
                
            except Exception as e:
                print(f"[工具执行器] 百度搜索工具注册失败: {e}")
        
        # 注册 Google 搜索工具
        if "google" in engines_to_register:
            try:
                from google_searcher import get_google_searcher
                
                google_searcher = get_google_searcher()
                priority_tag = " [优先]" if primary_engine == "google" else ""
                self.register_tool(
                    name="google_search",
                    function=google_searcher.search,
                    schema=google_searcher.get_tool_schema(),
                    description=f"Google搜索 - 获取国际信息和英文内容{priority_tag}"
                )
                print(f"[工具执行器] 已注册: google_search{priority_tag}")
                
            except Exception as e:
                print(f"[工具执行器] Google搜索工具注册失败: {e}")
        
        # 注册文档解析工具
        try:
            from document_parser import (
                get_document_parser_tool_schema,
                execute_document_parser_tool
            )
            
            self.register_tool(
                name="read_document",
                function=execute_document_parser_tool,
                schema=get_document_parser_tool_schema(),
                description="文档解析工具 - 读取PDF、图片(OCR)、文本文件内容"
            )
            print("[工具执行器] 已注册: read_document (文档解析)")
            
        except Exception as e:
            print(f"[工具执行器] 文档解析工具注册失败: {e}")
        
        # 注册系统时间工具
        try:
            from system_time_tool import get_system_time, TOOL_SCHEMA
            
            self.register_tool(
                name="get_system_time",
                function=get_system_time,
                schema=TOOL_SCHEMA,
                description="系统时间工具 - 获取当前日期、时间、星期等信息"
            )
            print("[工具执行器] 已注册: get_system_time (系统时间)")
            
        except Exception as e:
            print(f"[工具执行器] 系统时间工具注册失败: {e}")
    
    def register_tool(
        self,
        name: str,
        function: Callable,
        schema: Dict,
        description: str = ""
    ):
        """
        注册新工具
        
        Args:
            name: 工具名称（必须与 schema 中的 name 一致）
            function: 可调用的工具函数
            schema: 工具的 JSON Schema 定义
            description: 工具描述（可选）
        """
        self._tools[name] = function
        self._tool_schemas.append(schema)
        self._tool_descriptions[name] = description
        print(f"[工具执行器] 注册工具: {name}")
    
    def get_tool_schemas(self) -> List[Dict]:
        """
        获取所有工具的 Schema 列表
        
        Returns:
            List[Dict]: 工具 Schema 列表，可直接传给 LLM
        """
        return self._tool_schemas.copy()
    
    def get_available_tools(self) -> List[str]:
        """
        获取所有可用工具的名称列表
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 工具是否已注册
        """
        return tool_name in self._tools
    
    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数（字典格式）
        
        Returns:
            Dict: 工具执行结果
            {
                "success": bool,
                "tool_name": str,
                "result": Any,  # 工具返回的原始结果
                "result_json": str,  # 序列化后的 JSON 字符串
                "error": str  # 如果失败
            }
        """
        print(f"[工具执行器] 执行工具: {tool_name}")
        print(f"[工具执行器] 参数: {json.dumps(arguments, ensure_ascii=False)}")
        
        # 检查工具是否存在
        if not self.has_tool(tool_name):
            error_msg = f"工具 '{tool_name}' 未注册"
            print(f"[工具执行器] {error_msg}")
            return {
                "success": False,
                "tool_name": tool_name,
                "error": error_msg
            }
        
        try:
            # 获取工具函数
            tool_function = self._tools[tool_name]
            
            # 执行工具
            result = tool_function(**arguments)
            
            # 序列化结果为 JSON 字符串
            try:
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[工具执行器] JSON序列化失败，使用字符串: {e}")
                result_json = str(result)
            
            print(f"[工具执行器] 工具执行成功")
            
            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "result_json": result_json
            }
            
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            print(f"[工具执行器] {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "tool_name": tool_name,
                "error": error_msg
            }
    
    def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量执行多个工具调用
        
        Args:
            tool_calls: 工具调用列表，每项包含 function.name 和 function.arguments
        
        Returns:
            List[Dict]: 每个工具的执行结果列表
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                # 提取工具名称和参数
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                
                # 参数可能是字符串或字典
                arguments = function_info.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                
                # 执行工具
                result = self.execute_tool(tool_name, arguments)
                
                # 添加 tool_call_id（如果有）
                if "id" in tool_call:
                    result["tool_call_id"] = tool_call["id"]
                
                results.append(result)
                
            except Exception as e:
                print(f"[工具执行器] 工具调用解析失败: {e}")
                results.append({
                    "success": False,
                    "error": f"工具调用解析失败: {str(e)}"
                })
        
        return results
    
    def get_tool_info(self) -> str:
        """
        获取所有工具的信息摘要
        
        Returns:
            str: 工具信息字符串
        """
        info_lines = ["可用工具列表:"]
        for name, desc in self._tool_descriptions.items():
            info_lines.append(f"  - {name}: {desc}")
        return "\n".join(info_lines)


# 全局单例
_tool_executor = None


def get_tool_executor() -> ToolExecutor:
    """获取工具执行器的全局实例"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    快捷函数：执行工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
    
    Returns:
        Dict: 执行结果
    """
    executor = get_tool_executor()
    return executor.execute_tool(tool_name, arguments)


def get_all_tool_schemas() -> List[Dict]:
    """
    快捷函数：获取所有工具的 Schema
    
    Returns:
        List[Dict]: Schema 列表
    """
    executor = get_tool_executor()
    return executor.get_tool_schemas()

