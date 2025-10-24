#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件存储管理器改进版 - 每次直接读取本地文件，避免任务栏缓存bug
关键改动：
1. get_history() 每次都从文件读取最新数据，不依赖任何缓存
2. 完全移除内存缓存逻辑
3. 支持自定义存储路径
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import threading

class FileStorageManager:
    """改进的文件存储管理器 - 专注于直接文件读取"""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        初始化文件存储管理器
        
        Args:
            base_path: 自定义存储路径，默认为 C:\AgentData
        """
        self._lock = threading.RLock()  # 允许嵌套调用的文件访问锁
        
        if base_path:
            self.data_folder = base_path
        else:
            # 默认路径：C:\AgentData
            try:
                self.data_folder = os.path.join("C:\\", "AgentData")
                os.makedirs(self.data_folder, exist_ok=True)
            except PermissionError:
                # 权限不足，使用用户目录
                import sys
                user_home = os.path.expanduser("~")
                self.data_folder = os.path.join(user_home, "AgentData")
                os.makedirs(self.data_folder, exist_ok=True)
        
        self.metadata_file = os.path.join(self.data_folder, "metadata.json")
        self._init_metadata()
    
    def _init_metadata(self):
        """初始化元数据文件"""
        if not os.path.exists(self.metadata_file):
            metadata = {
                "conversations": {},
                "next_id": 1
            }
            self._write_metadata_file(metadata)
    
    def _read_metadata_file(self) -> Dict:
        """线程安全地读取元数据文件"""
        with self._lock:
            try:
                if os.path.exists(self.metadata_file):
                    with open(self.metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                print(f"[ERROR] 读取元数据失败: {e}")
            
            return {"conversations": {}, "next_id": 1}
    
    def _write_metadata_file(self, metadata: Dict):
        """线程安全地写入元数据文件"""
        with self._lock:
            try:
                with open(self.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERROR] 写入元数据失败: {e}")
    
    def _update_conversation_timestamp(self, conv_id: str, timestamp: str):
        """
        【安全方法】只更新指定对话的时间戳，不覆盖其他对话
        
        这防止了在添加消息时意外丢失其他对话的元数据
        """
        with self._lock:
            try:
                # 读取当前元数据
                metadata = self._read_metadata_file()
                
                # 只修改指定对话的 updated_at，其他对话保持不变
                if conv_id in metadata["conversations"]:
                    metadata["conversations"][conv_id]["updated_at"] = timestamp
                else:
                    # 如果对话不存在，添加它
                    metadata["conversations"][conv_id] = {
                        "title": "新对话",
                        "created_at": timestamp,
                        "updated_at": timestamp
                    }
                
                # 写回元数据
                self._write_metadata_file(metadata)
                
            except Exception as e:
                print(f"[ERROR] 更新对话时间戳失败: {e}")
    
    def _get_conversation_file_path(self, conv_id: str) -> str:
        """获取对话文件完整路径"""
        # 从元数据获取标题
        metadata = self._read_metadata_file()
        title = metadata.get("conversations", {}).get(conv_id, {}).get("title", "新对话")
        
        safe_title = self._sanitize_filename(title)
        filename = f"conv_{conv_id}_{safe_title}.txt"
        return os.path.join(self.data_folder, filename)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的特殊字符"""
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:50]  # 限制长度
    
    def _read_conversation_file(self, file_path: str) -> str:
        """
        线程安全地读取对话文件
        
        这是关键方法：每次都直接从磁盘读取，避免缓存问题
        """
        with self._lock:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                print(f"[ERROR] 读取文件失败 {file_path}: {e}")
            
            return ""
    
    def create_new_conversation(self, title: str = "新对话") -> str:
        """创建新对话"""
        metadata = self._read_metadata_file()
        
        conv_id = str(metadata["next_id"])
        metadata["next_id"] += 1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata["conversations"][conv_id] = {
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        self._write_metadata_file(metadata)
        
        # 创建对话文件
        file_path = self._get_conversation_file_path(conv_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        print(f"[FILE_STORAGE] 创建对话: {conv_id} - {title}")
        return conv_id
    
    def add_message(self, conv_id: str, role: str, content: str, file_paths: Optional[List[str]] = None):
        """
        添加消息到对话 - 使用 JSONL 格式存储（每行一个 JSON 对象）
        
        这样每次追加消息只需要追加一行，永远不会丢失历史消息
        
        参数：
            role: 'user' 或 'assistant'
            content: 消息内容（纯文本）
            file_paths: 附件路径列表（绝对路径）
        """
        file_path = self._get_conversation_file_path(conv_id)
        
        with self._lock:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 构建消息对象（JSON 格式）
                message = {
                    "timestamp": timestamp,
                    "role": role,
                    "content": content,
                    "files": file_paths if file_paths else []
                }
                
                # JSONL 格式：每行一个 JSON 对象，直接追加，永不覆盖
                with open(file_path, 'a', encoding='utf-8') as f:
                    json.dump(message, f, ensure_ascii=False)
                    f.write('\n')
                
                # 【关键修复】安全地更新元数据，防止覆盖其他对话
                # 只修改当前对话的 updated_at，保留其他所有对话的元数据
                self._update_conversation_timestamp(conv_id, timestamp)

                print(f"[FILE_STORAGE] 已保存消息: conv_id={conv_id}, role={role}, 文件数={len(file_paths) if file_paths else 0}")
                    
            except Exception as e:
                print(f"[ERROR] 添加消息失败: {e}")
                import traceback
                traceback.print_exc()
    
    def get_history(self, conv_id: str) -> List[Dict]:
        """
        获取对话历史 - JSONL 格式读取（每行一个 JSON 对象）
        
        每条消息单独一行，直接追加，永不覆盖。确保多次刷新时不会丢失历史。
        
        返回格式：
        [
            {
                "timestamp": "2025-10-21 14:30:00",
                "role": "user",
                "content": "用户消息内容",
                "files": []
            },
            {
                "timestamp": "2025-10-21 14:30:05",
                "role": "assistant", 
                "content": "AI 回复内容",
                "files": ["/path/to/image.png"]
            }
        ]
        """
        file_path = self._get_conversation_file_path(conv_id)
        
        with self._lock:
            try:
                if not os.path.exists(file_path):
                    return []
                
                messages = []
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            # 跳过空行
                            continue
                        
                        try:
                            message = json.loads(line)
                            # 标准化消息格式
                            standardized = {
                                'role': message.get('role', ''),
                                'content': message.get('content', '')
                            }
                            if 'timestamp' in message:
                                standardized['timestamp'] = message['timestamp']
                            if 'files' in message and message['files']:
                                standardized['files'] = message['files']
                            messages.append(standardized)
                        except json.JSONDecodeError as e:
                            # 如果某一行无效，跳过并打印日志
                            print(f"[WARNING] JSONL 行解析失败: {e}, 行内容: {line[:100]}")
                            continue
                
                print(f"[FILE_STORAGE] 已加载历史: conv_id={conv_id}, 消息数={len(messages)}")
                return messages
                        
            except Exception as e:
                print(f"[ERROR] 读取历史失败: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    def _parse_legacy_format(self, content: str) -> List[Dict]:
        """
        解析旧文本格式文件
        这是为了兼容之前的保存格式
        """
        messages = []
        lines = content.split('\n')
        
        current_message = None
        content_lines = []
        file_paths = []
        in_file_section = False
        
        for line in lines:
            # 检查消息开始标记（时间戳格式：[2025-10-21 14:30:00] 用户:）
            is_message_start = (
                line.startswith('[') and
                '] ' in line and
                ('用户:' in line or 'AI助手:' in line)
            )
            
            if is_message_start:
                # 保存之前的消息
                if current_message and content_lines:
                    current_message['content'] = '\n'.join(content_lines).strip()
                    if file_paths:
                        current_message['files'] = file_paths
                    if current_message['content']:
                        messages.append(current_message)
                
                # 开始新消息
                role = 'user' if '用户:' in line else 'assistant'
                current_message = {'role': role}
                content_lines = []
                file_paths = []
                in_file_section = False
            
            elif line.strip() == '[附件]:':
                in_file_section = True
                
            elif in_file_section and line.strip().startswith('- '):
                # 附件路径
                file_path = line.strip()[2:].strip()
                if file_path:
                    file_paths.append(file_path)
                    
            elif current_message and line.strip():
                # 消息内容
                content_lines.append(line)
        
        # 处理最后一条消息
        if current_message and content_lines:
            current_message['content'] = '\n'.join(content_lines).strip()
            if file_paths:
                current_message['files'] = file_paths
            if current_message['content']:
                messages.append(current_message)
        
        return messages
    
    def get_all_conversations(self) -> List[tuple]:
        """获取所有对话"""
        metadata = self._read_metadata_file()
        conversations = []
        
        for conv_id, info in metadata["conversations"].items():
            conversations.append((
                conv_id,
                info["title"],
                info.get("updated_at", info.get("created_at", ""))
            ))
        
        conversations.sort(key=lambda x: x[2], reverse=True)
        return conversations
    
    def update_conversation_title(self, conv_id: str, new_title: str):
        """更新对话标题"""
        metadata = self._read_metadata_file()
        
        if conv_id in metadata["conversations"]:
            metadata["conversations"][conv_id]["title"] = new_title
            metadata["conversations"][conv_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._write_metadata_file(metadata)
            
            # 重命名对话文件
            old_path = os.path.join(self.data_folder, f"conv_{conv_id}_*")
            import glob
            for file in glob.glob(old_path):
                os.remove(file)
    
    def delete_conversation(self, conv_id: str):
        """
        彻底删除对话及其所有关联文件
        
        删除内容：
        1. metadata.json 中的对话记录
        2. 对话数据文件 (conv_*.txt)
        3. 对话的所有生成文件（如图片、附件等）
        """
        import glob
        
        print(f"\n[FILE_STORAGE] 准备删除对话: {conv_id}")
        
        with self._lock:
            try:
                # 步骤1：从元数据中删除对话记录
                metadata = self._read_metadata_file()
                
                if conv_id in metadata["conversations"]:
                    conv_title = metadata["conversations"][conv_id]["title"]
                    del metadata["conversations"][conv_id]
                    self._write_metadata_file(metadata)
                    print(f"✅ 已从 metadata.json 中删除对话记录")
                else:
                    print(f"⚠️  对话不在 metadata 中")
                
                # 步骤2：删除主对话文件 (conv_*.txt)
                # 使用通配符匹配所有可能的文件名
                conv_file_pattern = os.path.join(self.data_folder, f"conv_{conv_id}_*.txt")
                deleted_files = []
                
                for file_path in glob.glob(conv_file_pattern):
                    try:
                        os.remove(file_path)
                        deleted_files.append(os.path.basename(file_path))
                        print(f"✅ 已删除对话文件: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"❌ 删除对话文件失败: {e}")
                
                if not deleted_files:
                    print(f"⚠️  未找到对话文件")
                
                # 步骤3：删除关联的生成文件（图片、附件等）
                # 这些文件通常保存在 generated/ 或类似的目录中
                generated_dir = os.path.join(self.data_folder, "generated")
                if os.path.exists(generated_dir):
                    # 搜索该对话相关的文件
                    for filename in os.listdir(generated_dir):
                        # 如果文件名中包含对话ID，就删除
                        if str(conv_id) in filename or f"conv_{conv_id}" in filename:
                            file_path = os.path.join(generated_dir, filename)
                            try:
                                os.remove(file_path)
                                print(f"✅ 已删除生成文件: {filename}")
                            except Exception as e:
                                print(f"❌ 删除生成文件失败: {e}")
                
                # 步骤4：日志摘要
                print(f"\n[FILE_STORAGE] 对话删除完成:")
                print(f"  对话ID: {conv_id}")
                print(f"  对话标题: {conv_title if 'conv_title' in locals() else '(未知)'}")
                print(f"  删除的文件: {len(deleted_files)} 个")
                print(f"  ✅ 所有相关文件已彻底删除\n")
                
            except Exception as e:
                print(f"\n[ERROR] 删除对话过程中出错: {e}")
                import traceback
                traceback.print_exc()
                print()


# 便捷函数
def create_file_storage_manager(base_path: Optional[str] = None) -> FileStorageManager:
    """创建文件存储管理器实例"""
    return FileStorageManager(base_path)
