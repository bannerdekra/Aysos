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
        
        # image_generator.py (使用SD控制台的真实成功配置)

        # 默认生成参数（基于SD控制台的成功案例）
        self.default_params = {
            # 1. 采样器：DPM++ 2M (SD控制台成功案例使用的)
            "sampler_name": "DPM++ 2M",
            "scheduler": "Karras",  # Schedule type
            
            # 2. 核心参数（与SD控制台完全一致）
            "steps": 50,
            "cfg_scale": 7,
            "seed": -1,
            "width": 512,
            "height": 512,
            "n_iter": 1,
            "batch_size": 1,
            "clip_skip": 2,  # SD控制台显示的关键参数
            
            # 3. 负面提示词
            "negative_prompt": "lowres, bad quality, deformed, blurry, worst quality",
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
            # 🚨 关键：强制绕过代理，直连本地 SD WebUI
            no_proxy = {'http': None, 'https': None}
            
            # 使用简单的进度API检查连接（更轻量）
            response = requests.get(
                f"{self.api_url}{self.progress_endpoint}", 
                timeout=5,
                proxies=no_proxy  # 🚨 绕过代理
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
            # 🚨 关键：强制绕过代理，直连本地 SD WebUI
            no_proxy = {'http': None, 'https': None}
            
            response = requests.get(
                f"{self.api_url}{self.progress_endpoint}",
                timeout=3,
                proxies=no_proxy  # 🚨 绕过代理
            )
            if response.status_code == 200:
                data = response.json()
                progress = data.get('progress', 0.0)
                # 返回进度和状态描述
                return progress, f"生成中... {int(progress * 100)}%"
        except:
            pass
        return 0.0, "准备中..."
    
    def switch_model(self, model_name: str) -> bool:
        """
        切换 SD WebUI 的模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否切换成功
        """
        try:
            # 🚨 绕过代理，直连本地 SD WebUI
            no_proxy = {'http': None, 'https': None}
            
            # 切换模型
            response = requests.post(
                f"{self.api_url}/sdapi/v1/options",
                json={"sd_model_checkpoint": model_name},
                timeout=30,
                proxies=no_proxy
            )
            
            if response.status_code == 200:
                print(f"[OK] 模型切换成功: {model_name}")
                return True
            else:
                print(f"[ERROR] 模型切换失败: 状态码 {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 模型切换异常: {e}")
            return False
    
    def generate_image_with_progress(self, prompt: str, progress_callback: Optional[Callable[[float, str], None]] = None,
                                    negative_prompt: Optional[str] = None, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """
        生成图像（带进度回调）
        
        Args:
            prompt: 正面提示词（英文）
            progress_callback: 进度回调函数 callback(progress: float, status: str)
            negative_prompt: 负面提示词（可选）
            **kwargs: 其他生成参数（包括 model 用于切换模型）
        
        Returns:
            (保存的图像路径, 错误信息)
        """
        # 🔍 如果指定了模型，先切换模型
        if 'model' in kwargs:
            model_name = kwargs.pop('model')  # 从 kwargs 中移除，不加入 payload
            print(f"[INFO] 切换模型到: {model_name}")
            self.switch_model(model_name)
        
        # 构建请求参数（完全复制 totally ok.py 的成功结构）
        payload = self.default_params.copy()
        payload["prompt"] = prompt
        
        # 如果提供了负面提示词，覆盖默认值
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        # 更新自定义参数
        payload.update(kwargs)
        
        print(f"[INFO] 开始生成图像...")
        print(f"[INFO] 使用 totally ok.py 的成功配置")
        
        # 🔍 关键调试：打印完整的发送给 SD 的请求
        print(f"\n{'='*70}")
        print(f"[DEBUG] ========== 发送给 SD WebUI 的完整请求 ==========")
        print(f"[DEBUG] API URL: {self.api_url}{self.txt2img_endpoint}")
        print(f"[DEBUG] 请求方法: POST")
        print(f"[DEBUG] 超时设置: 300 秒")
        print(f"\n[DEBUG] Payload JSON:")
        import json
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"[DEBUG] =====================================================")
        print(f"{'='*70}\n")
        
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
            # 🔍 发送请求（显式绕过代理）
            print(f"[INFO] 🚀 正在发送请求到 SD WebUI...")
            
            # 🚨 关键修复：强制绕过代理，直连本地 SD WebUI
            # 即使环境变量设置了 http_proxy（用于 Gemini），也不影响本地请求
            no_proxy = {
                'http': None,   # 不使用 HTTP 代理
                'https': None,  # 不使用 HTTPS 代理
            }
            
            # 发送生成请求（完全复制 totally ok.py 的方式 + 代理绕过）
            response = requests.post(
                url=f"{self.api_url}{self.txt2img_endpoint}",
                json=payload,
                timeout=300,  # 5分钟超时
                proxies=no_proxy  # 🚨 强制不使用代理
            )
            
            # 🔍 打印响应详情
            print(f"\n{'='*70}")
            print(f"[DEBUG] ========== SD WebUI 响应 ==========")
            print(f"[DEBUG] HTTP 状态码: {response.status_code}")
            print(f"[DEBUG] 响应头: Content-Type = {response.headers.get('Content-Type')}")
            print(f"[DEBUG] 响应大小: {len(response.content)} 字节")
            
            if response.status_code != 200:
                print(f"\n[ERROR] ❌ SD WebUI 返回错误状态码！")
                print(f"[ERROR] 状态码: {response.status_code}")
                print(f"[ERROR] 响应内容（前500字符）:")
                print(response.text[:500])
                print(f"[DEBUG] =======================================")
                print(f"{'='*70}\n")
            else:
                print(f"[OK] ✅ 请求成功！")
                print(f"[DEBUG] =======================================")
                print(f"{'='*70}\n")
            
            # 停止进度轮询
            generating = False
            progress_thread.join(timeout=1)
            
            # 检查响应状态（使用 totally ok.py 的方式）
            response.raise_for_status()  # 如果不是 2xx 会抛出异常
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
    
    def translate_prompt_via_ai(self, user_input: str, provider_name: str = None) -> Tuple[str, str]:
        """
        通过当前选中的 AI 模型翻译并优化用户输入为 SD 提示词
        
        Args:
            user_input: 用户的绘画描述
            provider_name: AI 提供商名称（deepseek/gemini），如果为 None 则自动检测
        
        Returns:
            (正面提示词, 负面提示词) 元组，限制在75个词以内
        """
        # 🔍 步骤1: 检测当前使用的 AI 模型
        try:
            from api_config import get_current_provider_name
            if provider_name is None:
                provider_name = get_current_provider_name()
            print(f"[OK] 当前 AI 模型: {provider_name}")
        except Exception as e:
            print(f"[ERROR] 获取 AI 模型失败: {e}")
            provider_name = 'deepseek'  # 默认值
        
        # 🔍 步骤2: 构建翻译请求（基于6GB显存限制）
        translation_prompt = f"""请将以下绘画描述转换为 Stable Diffusion 的英文提示词。

用户描述：{user_input}

【系统资源限制】：
- 用户显存：6GB
- 必须使用简单、基础的提示词
- 禁止复杂、高级的艺术风格词汇

【严格限制】：
1. 正面提示词：最多 20 个英文单词（包括逗号在内不超过25个token）
2. 负面提示词：最多 15 个英文单词
3. 【必须】只使用单个英文单词
4. 【必须】禁止 a, an, the, of, in, on, at
5. 【必须】每个单词用逗号和空格分隔

成功示例（SD控制台真实案例，7个token）：
1girl, white, shirt, blonde, hair, smile

正确示例（简单基础词汇）：
girl, standing, hair, long, eyes, blue, dress, white, smile, outdoor, simple, clean

错误示例（禁止）：
❌ long hair（词组）
❌ masterpiece, best quality（过于高级）
❌ cinematic lighting, ultra detailed（显存不足）

请严格遵守限制，直接输出两行提示词："""


        try:
            # 🔍 步骤3: 调用对应的 AI 模型获取提示词
            print(f"[INFO] 正在调用 {provider_name} 翻译提示词...")
            
            from api_client import get_ai_reply
            messages = [{'role': 'user', 'content': translation_prompt}]
            
            raw_prompt = get_ai_reply(messages)
            
            # 🔍 步骤4: 打印 AI 原始回复（用于调试）
            print(f"[DEBUG] ========== AI 原始回复 ==========")
            print(raw_prompt)
            print(f"[DEBUG] ====================================")
            
            # 🔍 步骤5: 检查是否是错误信息
            if raw_prompt.startswith("Error"):
                print(f"[ERROR] AI 调用失败: {raw_prompt}")
                raise Exception(f"AI 返回错误: {raw_prompt}")
            
            # 🔍 步骤6: 解析正面和负面提示词
            lines = [l.strip() for l in raw_prompt.split('\n') if l.strip()]
            
            positive_prompt = ""
            negative_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers"
            
            # 查找最像提示词的行
            for line in lines:
                if ',' in line and not line.startswith(('Error', '错误', '失败')):
                    if not positive_prompt:
                        positive_prompt = line
                    elif 'lowres' in line.lower() or 'bad' in line.lower():
                        negative_prompt = line
                        break
            
            if not positive_prompt:
                # 降级：使用第一行非空行
                positive_prompt = lines[0] if lines else ""
            
            # 🔍 步骤7: 清理提示词
            import re
            
            def clean_prompt(prompt_text: str) -> str:
                """清理提示词"""
                # 移除引号
                prompt_text = prompt_text.strip('"\'`')
                # 移除多余空格
                prompt_text = ' '.join(prompt_text.split())
                # 移除特殊字符（保留逗号、连字符、空格）
                prompt_text = re.sub(r'[^\w\s,\-]', '', prompt_text)
                return prompt_text
            
            positive_prompt = clean_prompt(positive_prompt)
            negative_prompt = clean_prompt(negative_prompt)
            
            # 🔍 步骤8: 严格限制单词数量（不超过 50 个英文单词）
            def count_words(prompt_text: str) -> int:
                """计算英文单词数量"""
                if not prompt_text:
                    return 0
                # 移除逗号和多余空格后计数
                words = prompt_text.replace(',', '').split()
                return len(words)
            
            def limit_to_max_words(prompt_text: str, max_words: int) -> str:
                """严格限制单词数量"""
                words_list = prompt_text.replace(',', '').split()
                
                if len(words_list) <= max_words:
                    return prompt_text
                
                print(f"[WARNING] 单词过多({len(words_list)}个)，截断到{max_words}个")
                
                # 截断到指定数量
                limited_words = words_list[:max_words]
                result = ', '.join(limited_words)
                
                print(f"[OK] 截断后: {len(limited_words)} 个单词")
                return result
            
            # 严格限制：正面 20 个单词，负面 15 个单词（保持在25 tokens以内）
            positive_prompt = limit_to_max_words(positive_prompt, max_words=20)
            negative_prompt = limit_to_max_words(negative_prompt, max_words=15)
            
            # 🔍 步骤9: 验证提示词有效性
            if not positive_prompt or len(positive_prompt.strip()) < 5:
                print(f"[ERROR] 正面提示词无效，使用降级方案")
                positive_prompt = f"simple, clean, {user_input}"
                positive_prompt = limit_to_max_words(positive_prompt, max_words=20)
            
            # 🔍 步骤10: 计算总token数并打印
            pos_words = count_words(positive_prompt)
            neg_words = count_words(negative_prompt)
            pos_tokens = pos_words + positive_prompt.count(',')
            neg_tokens = neg_words + negative_prompt.count(',')
            
            print(f"[OK] ========== 最终提示词 ==========")
            print(f"[OK] 正面提示词 ({pos_words} 单词, {pos_tokens} tokens):")
            print(f"     {positive_prompt}")
            print(f"[OK] 负面提示词 ({neg_words} 单词, {neg_tokens} tokens):")
            print(f"     {negative_prompt}")
            print(f"[OK] 总计: {pos_tokens + neg_tokens} tokens (限制: ≤45 tokens)")
            print(f"[OK] =====================================")
            
            if pos_tokens > 25 or neg_tokens > 20:
                print(f"[WARNING] ⚠️  token数量超过限制！")
                print(f"[WARNING] 正面: {pos_tokens}/25 tokens, 负面: {neg_tokens}/20 tokens")
            
            return positive_prompt, negative_prompt
            
        except Exception as e:
            # 🔍 步骤11: 错误处理
            print(f"[ERROR] AI 翻译失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 降级：使用原始输入
            fallback_positive = f"masterpiece, best quality, {user_input}"
            fallback_negative = "lowres, bad anatomy, bad hands, text, error, missing fingers"
            
            print(f"[WARNING] 使用降级方案:")
            print(f"          正面: {fallback_positive}")
            print(f"          负面: {fallback_negative}")
            
            return fallback_positive, fallback_negative


# 全局实例
_image_generator = None

def get_image_generator() -> ImageGenerator:
    """获取图像生成器单例"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
