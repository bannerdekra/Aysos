"""
百度千帆搜索工具
封装百度千帆 AI Search API，提供实时网络搜索能力
支持 Function Calling 的工具定义和执行
"""
import os
import requests
import json
from typing import Dict, Any, Optional, List


class BaiduSearcher:
    """百度千帆搜索工具类"""
    
    # 工具的 JSON Schema 定义（供 LLM 理解）
    TOOL_SCHEMA = {
        "type": "function",
        "function": {
            "name": "baidu_search",
            "description": "使用百度搜索获取实时网络信息。当用户询问最新资讯、实时数据、当前事件、天气、新闻或需要从互联网获取信息时使用此工具。支持时效性过滤和网站限定，可提高查询准确性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询关键词，应该是清晰、具体的搜索问题。例如：'广州今天天气'、'Python 3.13 新特性'"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回的搜索结果数量，默认为5，范围1-10",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    },
                    "search_recency_filter": {
                        "type": "string",
                        "description": "根据发布时间筛选网页结果，适用于实时信息查询。可选值：'day'(最近一天)、'week'(最近一周)、'month'(最近一月)、'year'(最近一年)。查询天气、新闻等实时信息时强烈建议使用此参数。",
                        "enum": ["day", "week", "month", "year"]
                    },
                    "site_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "限定搜索结果只来自指定的权威网站列表，最多支持20个站点。例如：['www.weather.com.cn'] 用于查询天气，['github.com'] 用于查询开源项目。提高特定领域查询的准确率。",
                        "maxItems": 20
                    }
                },
                "required": ["query"]
            }
        }
    }
    
    def __init__(self):
        """初始化百度搜索工具"""
        self.api_key = os.getenv("Baidu Search-APIKEY")
        self.base_url = "https://qianfan.baidubce.com"
        self.search_endpoint = "/v2/ai_search/web_search"
        
        if not self.api_key:
            print("[百度搜索] 环境变量 'Baidu Search-APIKEY' 未设置")
        else:
            print("[百度搜索] API Key 已加载")
        
        # 自动禁用代理（百度搜索是国内服务）
        self._disable_proxy()
    
    def _disable_proxy(self):
        """禁用代理"""
        try:
            from api_config import disable_proxy
            disable_proxy()
            print("[百度搜索] 已禁用代理（国内服务）")
        except Exception as e:
            print(f"[百度搜索] 代理配置失败: {e}")
    
    def get_tool_schema(self) -> Dict:
        """
        获取工具的 Schema 定义
        
        Returns:
            Dict: 工具 Schema
        """
        return self.TOOL_SCHEMA
    
    def search(self, query: str, top_k: int = 5, 
               search_recency_filter: Optional[str] = None,
               site_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        执行百度搜索
        
        Args:
            query: 搜索查询关键词
            top_k: 返回的搜索结果数量（默认5，范围1-10）
            search_recency_filter: 时效性过滤（可选：'day'/'week'/'month'/'year'）
                - 'day': 最近一天
                - 'week': 最近一周
                - 'month': 最近一月
                - 'year': 最近一年
            site_filter: 网站过滤列表（可选，最多20个站点）
                例如：['www.weather.com.cn'] 用于天气查询
        
        Returns:
            Dict: 搜索结果
            {
                "success": bool,
                "data": {
                    "summary": str,  # AI 生成的摘要
                    "results": [     # 搜索结果列表
                        {
                            "title": str,
                            "url": str,
                            "content": str
                        }
                    ]
                },
                "error": str  # 如果失败
            }
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "百度搜索 API Key 未配置"
            }
        
        try:
            # 构建请求体
            payload = {
                "messages": [
                    {
                        "content": query,
                        "role": "user"
                    }
                ],
                "search_source": "baidu_search_v2",
                "resource_type_filter": [
                    {
                        "type": "web",
                        "top_k": top_k
                    }
                ]
            }
            
            # 添加可选参数：时效性过滤
            if search_recency_filter:
                payload["search_recency_filter"] = search_recency_filter
                print(f"[百度搜索] 🕒 时效性过滤: {search_recency_filter}")
            
            # 添加可选参数：网站过滤
            if site_filter:
                payload["search_filter"] = {
                    "match": {
                        "site": site_filter
                    }
                }
                print(f"[百度搜索] 🌐 网站过滤: {', '.join(site_filter)}")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送请求
            url = f"{self.base_url}{self.search_endpoint}"
            print(f"[百度搜索] 📡 搜索: {query}")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            parsed_result = self._parse_response(result)
            
            print(f"[百度搜索] 成功获取 {len(parsed_result.get('data', {}).get('results', []))} 条结果")
            return parsed_result
            
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请稍后重试"
            print(f"[百度搜索] {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            print(f"[百度搜索] ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        except Exception as e:
            error_msg = f"搜索失败: {str(e)}"
            print(f"[百度搜索] ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def _parse_response(self, response: Dict) -> Dict[str, Any]:
        """
        解析百度千帆 API 响应
        
        Args:
            response: API 原始响应
        
        Returns:
            Dict: 格式化后的搜索结果
        """
        try:
            # 【修正】根据实际 API 响应结构解析
            # 实际响应结构: {"request_id": "...", "references": [...]}
            
            # 提取搜索结果（从 references 字段）
            results = []
            if "references" in response:
                for item in response["references"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "snippet": item.get("snippet", ""),  # 摘要文本
                        "date": item.get("date", ""),  # 发布日期
                        "website": item.get("website", ""),  # 来源网站
                        "type": item.get("type", "web")  # 资源类型
                    })
            
            # 生成简单的摘要（取第一条结果的 snippet 或 content）
            summary = ""
            if results:
                first_result = results[0]
                summary = first_result.get("snippet") or first_result.get("content", "")
                # 限制摘要长度
                if len(summary) > 500:
                    summary = summary[:500] + "..."
            
            return {
                "success": True,
                "data": {
                    "summary": summary,
                    "results": results
                }
            }
            
        except Exception as e:
            print(f"[百度搜索] ⚠️ 响应解析失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"响应解析失败: {str(e)}"
            }
    
    @classmethod
    def get_schema(cls) -> Dict:
        """获取工具的 JSON Schema"""
        return cls.TOOL_SCHEMA
    
    def __call__(self, query: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """
        使工具可以像函数一样被调用
        
        Args:
            query: 搜索查询
            top_k: 结果数量
            **kwargs: 其他参数
        
        Returns:
            Dict: 搜索结果
        """
        return self.search(query=query, top_k=top_k, **kwargs)


# 全局实例
_baidu_searcher = None


def get_baidu_searcher() -> BaiduSearcher:
    """获取百度搜索工具的全局实例"""
    global _baidu_searcher
    if _baidu_searcher is None:
        _baidu_searcher = BaiduSearcher()
    return _baidu_searcher


def baidu_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    快捷函数：执行百度搜索
    
    Args:
        query: 搜索查询
        top_k: 结果数量
    
    Returns:
        Dict: 搜索结果
    """
    searcher = get_baidu_searcher()
    return searcher.search(query=query, top_k=top_k)


