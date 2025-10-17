"""
文档解析工具
支持解析 PDF、图片等文件格式
"""

import os
import json
from typing import Dict, Any, List, Optional


class DocumentParser:
    """文档解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.supported_formats = {
            'pdf': ['.pdf'],
            'image': ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'],
            'text': ['.txt', '.md', '.json', '.xml', '.html', '.csv']
        }
    
    def is_supported(self, file_path: str) -> bool:
        """检查文件是否支持解析"""
        ext = os.path.splitext(file_path)[1].lower()
        for formats in self.supported_formats.values():
            if ext in formats:
                return True
        return False
    
    def get_file_type(self, file_path: str) -> Optional[str]:
        """获取文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        for file_type, formats in self.supported_formats.items():
            if ext in formats:
                return file_type
        return None
    
    def parse_pdf(self, file_path: str, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        解析 PDF 文件
        
        Args:
            file_path: PDF 文件路径
            pages: 要解析的页码列表（从1开始），None 表示解析所有页
            
        Returns:
            包含文本内容的字典
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return {
                "success": False,
                "error": "未安装 PyMuPDF 库，请运行: pip install PyMuPDF"
            }
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # 确定要解析的页码
            if pages:
                pages_to_parse = [p - 1 for p in pages if 1 <= p <= total_pages]
            else:
                pages_to_parse = list(range(total_pages))
            
            # 提取文本
            content = []
            for page_num in pages_to_parse:
                page = doc[page_num]
                text = page.get_text()
                content.append({
                    "page": page_num + 1,
                    "text": text.strip()
                })
            
            doc.close()
            
            return {
                "success": True,
                "file_type": "pdf",
                "total_pages": total_pages,
                "parsed_pages": len(content),
                "content": content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF 解析失败: {str(e)}"
            }
    
    def parse_image(self, file_path: str, use_ocr: bool = True) -> Dict[str, Any]:
        """
        解析图片文件
        
        Args:
            file_path: 图片文件路径
            use_ocr: 是否使用 OCR 识别文字
            
        Returns:
            包含图片信息和文字内容的字典
        """
        try:
            from PIL import Image
        except ImportError:
            return {
                "success": False,
                "error": "未安装 Pillow 库，请运行: pip install Pillow"
            }
        
        try:
            img = Image.open(file_path)
            
            result = {
                "success": True,
                "file_type": "image",
                "format": img.format,
                "size": img.size,  # (width, height)
                "mode": img.mode
            }
            
            # OCR 文字识别
            if use_ocr:
                try:
                    import pytesseract
                    
                    # 识别文字
                    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                    result["text"] = text.strip()
                    result["ocr_enabled"] = True
                    
                except ImportError:
                    result["text"] = ""
                    result["ocr_enabled"] = False
                    result["ocr_error"] = "未安装 pytesseract 库，请运行: pip install pytesseract"
                except Exception as e:
                    result["text"] = ""
                    result["ocr_enabled"] = False
                    result["ocr_error"] = f"OCR 识别失败: {str(e)}"
            else:
                result["text"] = ""
                result["ocr_enabled"] = False
            
            img.close()
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"图片解析失败: {str(e)}"
            }
    
    def parse_text(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        解析文本文件
        
        Args:
            file_path: 文本文件路径
            encoding: 文件编码
            
        Returns:
            包含文本内容的字典
        """
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            return {
                "success": True,
                "file_type": "text",
                "encoding": encoding,
                "size": len(content),
                "lines": len(content.split('\n')),
                "content": content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"文本文件解析失败: {str(e)}"
            }
    
    def parse_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        自动识别并解析文件
        
        Args:
            file_path: 文件路径
            **kwargs: 额外参数（如 pages, use_ocr 等）
            
        Returns:
            解析结果字典
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        file_type = self.get_file_type(file_path)
        
        if not file_type:
            return {
                "success": False,
                "error": f"不支持的文件格式: {os.path.splitext(file_path)[1]}"
            }
        
        # 根据文件类型调用对应的解析方法
        if file_type == 'pdf':
            return self.parse_pdf(file_path, pages=kwargs.get('pages'))
        elif file_type == 'image':
            return self.parse_image(file_path, use_ocr=kwargs.get('use_ocr', True))
        elif file_type == 'text':
            return self.parse_text(file_path, encoding=kwargs.get('encoding', 'utf-8'))
        else:
            return {
                "success": False,
                "error": f"未实现的文件类型解析: {file_type}"
            }


# 单例模式
_document_parser = None

def get_document_parser() -> DocumentParser:
    """获取文档解析器实例"""
    global _document_parser
    if _document_parser is None:
        _document_parser = DocumentParser()
    return _document_parser


def get_document_parser_tool_schema() -> Dict[str, Any]:
    """
    获取文档解析工具的 Schema
    用于 Function Calling
    """
    return {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "读取并解析文档内容，支持 PDF（提取文字）、图片（OCR识别）、文本文件等。注意：需要用户先通过界面上传文件获得 file_id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "用户上传的文件ID（文件路径）"
                    },
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "（仅PDF）要读取的页码列表，从1开始。例如 [1, 2, 3]。不指定则读取全部页面"
                    },
                    "use_ocr": {
                        "type": "boolean",
                        "description": "（仅图片）是否使用OCR识别图片中的文字，默认 true"
                    }
                },
                "required": ["file_id"]
            }
        }
    }


def execute_document_parser_tool(arguments: Dict[str, Any]) -> str:
    """
    执行文档解析工具
    
    Args:
        arguments: 工具参数
        
    Returns:
        JSON 格式的解析结果
    """
    file_id = arguments.get('file_id')
    pages = arguments.get('pages')
    use_ocr = arguments.get('use_ocr', True)
    
    parser = get_document_parser()
    
    # 解析文件
    result = parser.parse_file(file_id, pages=pages, use_ocr=use_ocr)
    
    # 格式化输出
    if result.get('success'):
        if result.get('file_type') == 'pdf':
            output = f"✅ PDF 解析成功\n"
            output += f"📄 总页数: {result.get('total_pages')}\n"
            output += f"📖 已解析: {result.get('parsed_pages')} 页\n\n"
            
            for page_data in result.get('content', []):
                output += f"--- 第 {page_data['page']} 页 ---\n"
                output += page_data['text'][:500]  # 限制长度
                if len(page_data['text']) > 500:
                    output += "\n...(内容过长，已截断)"
                output += "\n\n"
        
        elif result.get('file_type') == 'image':
            output = f"✅ 图片解析成功\n"
            output += f"📐 尺寸: {result.get('size')[0]}x{result.get('size')[1]}\n"
            output += f"🎨 格式: {result.get('format')}\n"
            
            if result.get('ocr_enabled'):
                output += f"\n📝 OCR 识别结果:\n{result.get('text', '(未识别到文字)')}"
            else:
                output += f"\n⚠️ OCR 未启用: {result.get('ocr_error', '')}"
        
        elif result.get('file_type') == 'text':
            output = f"✅ 文本文件解析成功\n"
            output += f"📊 大小: {result.get('size')} 字符\n"
            output += f"📄 行数: {result.get('lines')}\n\n"
            content = result.get('content', '')
            output += content[:1000]  # 限制长度
            if len(content) > 1000:
                output += "\n...(内容过长，已截断)"
        
        else:
            output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output = f"❌ 解析失败: {result.get('error')}"
    
    return output


if __name__ == '__main__':
    # 测试代码
    parser = get_document_parser()
    
    # 测试支持的格式
    print("支持的格式:")
    print(json.dumps(parser.supported_formats, ensure_ascii=False, indent=2))
    
    # 测试文件类型检测
    test_files = [
        "test.pdf",
        "image.png",
        "document.txt",
        "unknown.xyz"
    ]
    
    print("\n文件类型检测:")
    for file in test_files:
        file_type = parser.get_file_type(file)
        supported = parser.is_supported(file)
        print(f"{file}: type={file_type}, supported={supported}")
