"""
Stable Diffusion 图像生成管理器
负责与本地 SD WebUI API 通信，生成图像
参考 creat.py 的正确实现方式
"""
import os
import requests
import json
import base64
import io
import time
from datetime import datetime
from PIL import Image
from typing import Optional, Dict, Any, Tuple, Callable

class ImageGenerator:
    """Stable Diffusion 图像生成器"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:7860"):
        """
        初始化图像生成器
        
        Args:
            api_url: SD WebUI API 地址
        """
        self.api_url = api_url
        self.txt2img_endpoint = "/sdapi/v1/txt2img"
        self.progress_endpoint = "/sdapi/v1/progress"
        
        # 默认生成参数（参考 creat.py）
        self.default_params = {
            "steps": 30,
            "sampler_name": "DPM++ 2M Karras",
            "cfg_scale": 7.0,
            "seed": -1,
            "width": 512,
            "height": 512,
            "n_iter": 1,
            "batch_size": 1,
            "negative_prompt": "lowres, deformed, jpeg artifacts, blurry, worst quality",
            "override_settings": {
                "sd_model_checkpoint": "v1-5-pruned-emaonly"
            }
        }
        
        # 创建桌面Art文件夹
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self.art_folder = os.path.join(desktop, "Art")
        os.makedirs(self.art_folder, exist_ok=True)
        print(f"[OK] 艺术作品保存目录: {self.art_folder}")
    
    def check_connection(self) -> Tuple[bool, str]:
        """
        检查 SD WebUI API 连接状态
        
        Returns:
            (是否连接成功, 提示信息)
        """
        try:
            # 使用简单的进度API检查连接（更轻量）
            response = requests.get(
                f"{self.api_url}{self.progress_endpoint}", 
                timeout=5
            )
            
            if response.status_code == 200:
                return True, "✅ SD WebUI 连接成功"
            else:
                return False, f"❌ SD WebUI 返回状态码 {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, f"❌ 无法连接到 {self.api_url}，请确保 SD WebUI 已启动"
        except requests.exceptions.Timeout:
            return False, "❌ 连接超时，请检查 SD WebUI 是否正在运行"
        except Exception as e:
            return False, f"❌ 连接错误: {str(e)}"
    
    def get_progress(self) -> Tuple[float, str]:
        """
        获取当前生成进度
        
        Returns:
            (进度值 0.0-1.0, 当前状态描述)
        """
        try:
            response = requests.get(
                f"{self.api_url}{self.progress_endpoint}",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                progress = data.get('progress', 0.0)
                # 返回进度和状态描述
                return progress, f"生成中... {int(progress * 100)}%"
        except:
            pass
        return 0.0, "准备中..."
    
    def generate_image_with_progress(self, prompt: str, progress_callback: Optional[Callable[[float, str], None]] = None,
                                    negative_prompt: Optional[str] = None, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """
        生成图像（带进度回调）
        
        Args:
            prompt: 正面提示词（英文）
            progress_callback: 进度回调函数 callback(progress: float, status: str)
            negative_prompt: 负面提示词（可选）
            **kwargs: 其他生成参数
        
        Returns:
            (保存的图像路径, 错误信息)
        """
        # 构建请求参数（参考 creat.py 的 PAYLOAD 结构）
        payload = self.default_params.copy()
        payload["prompt"] = prompt
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        # 更新自定义参数
        payload.update(kwargs)
        
        print(f"[INFO] 开始生成图像...")
        print(f"[INFO] 提示词: {prompt[:100]}...")
        print(f"[INFO] 提示词完整长度: {len(prompt)} 字符")
        
        # 🔍 调试输出：打印完整 payload
        print(f"[DEBUG] API URL: {self.api_url}{self.txt2img_endpoint}")
        print(f"[DEBUG] Payload 键: {list(payload.keys())}")
        print(f"[DEBUG] 完整提示词: {prompt}")  # 打印完整提示词
        print(f"[DEBUG] Payload 详情:")
        import json
        # 完整打印，不截断
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # 创建进度轮询线程标志
        generating = True
        
        def poll_progress():
            """轮询进度的内部函数"""
            last_progress = 0.0
            while generating:
                try:
                    progress, status = self.get_progress()
                    # 只在进度变化时回调
                    if progress > last_progress and progress_callback:
                        progress_callback(progress, status)
                        last_progress = progress
                    
                    # 如果进度达到100%，等待主线程完成
                    if progress >= 1.0:
                        break
                    
                    time.sleep(0.5)  # 每0.5秒轮询一次
                except Exception as e:
                    print(f"[DEBUG] 进度轮询异常: {e}")
                    time.sleep(0.5)
        
        # 启动进度轮询线程
        import threading
        progress_thread = threading.Thread(target=poll_progress, daemon=True)
        progress_thread.start()
        
        try:
            # 🔍 调试输出：请求前
            print(f"[DEBUG] 发送 POST 请求到 {self.api_url}{self.txt2img_endpoint}")
            
            # 发送生成请求（阻塞式，参考 creat.py）
            response = requests.post(
                url=f"{self.api_url}{self.txt2img_endpoint}",
                json=payload,
                timeout=300  # 5分钟超时
            )
            
            # 🔍 调试输出：响应状态
            print(f"[DEBUG] 响应状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"[DEBUG] 响应内容: {response.text[:500]}")
            
            # 停止进度轮询
            generating = False
            progress_thread.join(timeout=1)
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"❌ SD WebUI 返回状态码 {response.status_code}"
                # 尝试提取错误详情
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f"\n详细错误: {error_data['error']}"
                except:
                    pass
                return None, error_msg
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get('images'):
                return None, "❌ 未接收到图像数据"
            
            # 最终进度回调
            if progress_callback:
                progress_callback(1.0, "✅ 生成完成，正在保存...")
            
            # 解码并保存图像（参考 creat.py）
            image_b64 = result['images'][0]
            image_data = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_data))
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"art_{timestamp}.png"
            filepath = os.path.join(self.art_folder, filename)
            
            # 保存图像
            image.save(filepath, "PNG")
            
            print(f"[OK] 图像已保存: {filepath}")
            print(f"[INFO] 图像尺寸: {image.size[0]}x{image.size[1]}")
            
            return filepath, None
            
        except requests.exceptions.Timeout:
            generating = False
            return None, "❌ 生成超时（5分钟），请稍后重试"
        except requests.exceptions.RequestException as e:
            generating = False
            return None, f"❌ 请求失败: {str(e)}"
        except Exception as e:
            generating = False
            return None, f"❌ 生成错误: {str(e)}"
    
    def translate_prompt_via_ai(self, user_input: str, ai_reply_func) -> str:
        """
        通过 AI 翻译并优化用户输入为 SD 提示词
        
        Args:
            user_input: 用户的绘画描述
            ai_reply_func: AI 回复函数
        
        Returns:
            优化后的英文提示词（限制在150字符以内）
        """
        # 构建翻译请求
        translation_prompt = f"""请将以下绘画描述转换为 Stable Diffusion 的英文提示词。

用户描述：{user_input}

要求：
1. 提取关键视觉元素（人物、场景、风格、光影等）
2. 翻译成准确的英文提示词
3. 使用逗号分隔各个元素
4. 添加画质增强词（如 masterpiece, best quality, detailed）
5. 保持简洁，不超过100个单词
6. 只返回最终的提示词，不要任何解释

格式示例：masterpiece, best quality, 1girl, long hair, blue eyes, white dress, beach, sunset

请直接输出提示词："""

        try:
            # 调用 AI 获取提示词
            messages = [{'role': 'user', 'content': translation_prompt}]
            raw_prompt = ai_reply_func(messages)
            
            print(f"[DEBUG] AI 原始回复: {repr(raw_prompt)}")
            
            # 清理提示词
            prompt = raw_prompt.strip()
            
            # 移除可能的引号
            prompt = prompt.strip('"\'`')
            
            # 移除可能的解释性文本（只取第一行）
            if '\n' in prompt:
                lines = [l.strip() for l in prompt.split('\n') if l.strip()]
                # 找到最像提示词的一行（包含逗号或masterpiece等关键词）
                for line in lines:
                    if ',' in line or 'masterpiece' in line.lower() or 'best quality' in line.lower():
                        prompt = line
                        break
                else:
                    prompt = lines[0] if lines else prompt
            
            # 移除可能导致问题的字符
            # 移除多余的空格
            prompt = ' '.join(prompt.split())
            
            # 移除不必要的标点（保留逗号和连字符）
            import re
            prompt = re.sub(r'[^\w\s,\-]', '', prompt)
            
            # 限制长度（避免过长提示词导致502）
            max_length = 200  # 字符限制
            if len(prompt) > max_length:
                print(f"[WARNING] 提示词过长({len(prompt)}字符)，截断到{max_length}字符")
                # 在最后一个逗号处截断
                truncated = prompt[:max_length]
                last_comma = truncated.rfind(',')
                if last_comma > 0:
                    prompt = truncated[:last_comma]
                else:
                    prompt = truncated
            
            # 验证提示词有效性
            if not prompt or len(prompt.strip()) < 5:
                print(f"[WARNING] AI 提示词无效，使用降级方案")
                prompt = f"masterpiece, best quality, {user_input}"
            
            print(f"[OK] AI 优化提示词: {prompt}")
            print(f"[OK] 提示词长度: {len(prompt)} 字符")
            return prompt
            
        except Exception as e:
            print(f"[WARNING] AI 翻译失败: {e}")
            import traceback
            traceback.print_exc()
            # 降级：使用原始输入
            return f"masterpiece, best quality, {user_input}"


# 全局实例
_image_generator = None

def get_image_generator() -> ImageGenerator:
    """获取图像生成器单例"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
