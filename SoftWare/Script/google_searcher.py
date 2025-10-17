"""
Google 搜索工具
使用 Google Custom Search API 进行网络搜索
"""

import os
import requests
from typing import Dict, List, Optional, Any


class GoogleSearcher:
    """Google 搜索工具封装"""
    
    def __init__(self):
        """初始化 Google 搜索工具"""
        # 从环境变量获取 API Key 和 Search Engine ID
        # 支持两种环境变量名称（兼容性）
        self.api_key = os.getenv("Google search-APIKEY") or os.getenv("GOOGLE_SEARCH_APIKEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        if not self.api_key:
            print("[Google搜索] ⚠️ 环境变量 'Google search-APIKEY' 或 'GOOGLE_SEARCH_APIKEY' 未设置")
        else:
            print("[Google搜索] ✅ API Key 已加载")
        
        if not self.search_engine_id:
            print("[Google搜索] ⚠️ 环境变量 'GOOGLE_SEARCH_ENGINE_ID' 未设置")
        else:
            print(f"[Google搜索] ✅ Search Engine ID 已加载: {self.search_engine_id[:10]}...")
        
        # 🔧 自动启用代理（Google 需要代理）
        self._enable_proxy()
    
    def _enable_proxy(self):
        """启用代理"""
        try:
            from api_config import enable_proxy
            enable_proxy()
            print("[Google搜索] 🌐 已启用代理")
        except Exception as e:
            print(f"[Google搜索] ⚠️ 代理启用失败: {e}")
    
    def search(self, query: str, num: int = 5, **kwargs) -> Dict[str, Any]:
        """
        执行 Google 搜索
        
        Args:
            query: 搜索查询关键词
            num: 返回的搜索结果数量（默认5，最大10）
            **kwargs: 其他可选参数（如 dateRestrict 等）
        
        Returns:
            Dict: 搜索结果
            {
                "success": True/False,
                "data": {
                    "summary": "摘要",
                    "results": [
                        {
                            "title": "标题",
                            "url": "链接",
                            "snippet": "摘要",
                            "displayLink": "显示链接"
                        },
                        ...
                    ]
                },
                "error": "错误信息"  # 仅在失败时
            }
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Search API Key 未配置。请设置环境变量 'Google search-APIKEY' 或 'GOOGLE_SEARCH_APIKEY'"
            }
        
        if not self.search_engine_id:
            return {
                "success": False,
                "error": "Google Search Engine ID 未配置。请设置环境变量 'GOOGLE_SEARCH_ENGINE_ID'"
            }
        
        try:
            # 限制结果数量
            num = min(num, 10)
            
            print(f"[Google搜索] 📡 搜索: {query}")
            
            # 构建请求参数
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": num
            }
            
            # 添加其他可选参数
            if 'dateRestrict' in kwargs:
                params['dateRestrict'] = kwargs['dateRestrict']
                print(f"[Google搜索] 🕒 时间限制: {kwargs['dateRestrict']}")
            
            if 'siteSearch' in kwargs:
                params['siteSearch'] = kwargs['siteSearch']
                print(f"[Google搜索] 🌐 站点限制: {kwargs['siteSearch']}")
            
            # 发送请求
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 解析响应
            return self._parse_response(data)
            
        except requests.exceptions.RequestException as e:
            print(f"[Google搜索] ❌ 请求失败: {e}")
            return {
                "success": False,
                "error": f"搜索请求失败: {str(e)}"
            }
        except Exception as e:
            print(f"[Google搜索] ❌ 未知错误: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}"
            }
    
    def _parse_response(self, response: Dict) -> Dict[str, Any]:
        """
        解析 Google Custom Search API 响应
        
        Args:
            response: API 原始响应
        
        Returns:
            Dict: 格式化后的搜索结果
        """
        try:
            # Google 响应结构:
            # {
            #   "items": [
            #     {
            #       "title": "...",
            #       "link": "...",
            #       "snippet": "...",
            #       "displayLink": "..."
            #     }
            #   ]
            # }
            
            results = []
            if "items" in response:
                for item in response["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "displayLink": item.get("displayLink", ""),
                        "formattedUrl": item.get("formattedUrl", "")
                    })
            
            # 生成摘要（取第一条结果的 snippet）
            summary = ""
            if results:
                summary = results[0].get("snippet", "")
                if len(summary) > 500:
                    summary = summary[:500] + "..."
            
            print(f"[Google搜索] ✅ 成功获取 {len(results)} 条结果")
            
            return {
                "success": True,
                "data": {
                    "summary": summary,
                    "results": results
                }
            }
            
        except Exception as e:
            print(f"[Google搜索] ⚠️ 响应解析失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"响应解析失败: {str(e)}"
            }
    
    def get_tool_schema(self) -> Dict:
        """
        获取工具的 OpenAI Function Calling Schema
        
        Returns:
            Dict: 工具 Schema 定义
        """
        return {
            "type": "function",
            "function": {
                "name": "google_search",
                "description": (
                    "使用 Google 搜索引擎搜索实时信息、新闻、资料等。"
                    "适用场景：查询最新信息、国际新闻、技术文档、学术资料等。"
                    "相比百度搜索，Google 更适合搜索英文内容和国际信息。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询关键词（支持中英文）"
                        },
                        "num": {
                            "type": "integer",
                            "description": "返回的结果数量（默认5，最大10）",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 10
                        },
                        "dateRestrict": {
                            "type": "string",
                            "description": (
                                "时间限制（可选）：\n"
                                "- 'd[number]': 最近N天（如 'd7' 表示最近7天）\n"
                                "- 'w[number]': 最近N周（如 'w1' 表示最近1周）\n"
                                "- 'm[number]': 最近N月（如 'm1' 表示最近1个月）\n"
                                "- 'y[number]': 最近N年（如 'y1' 表示最近1年）"
                            ),
                            "enum": ["d1", "d7", "w1", "m1", "m6", "y1"]
                        },
                        "siteSearch": {
                            "type": "string",
                            "description": "限制搜索特定网站（可选），如 'github.com'"
                        }
                    },
                    "required": ["query"]
                }
            }
        }


# 单例模式
_google_searcher_instance = None

def get_google_searcher() -> GoogleSearcher:
    """获取 Google 搜索工具单例"""
    global _google_searcher_instance
    if _google_searcher_instance is None:
        _google_searcher_instance = GoogleSearcher()
    return _google_searcher_instance
