import os
import json
from datetime import datetime
from typing import List, Dict, Optional

class FileManager:
    """文件存储管理器，处理txt文件的聊天记录存储"""
    
    def __init__(self, data_folder="AgentData"):
        """
        初始化文件管理器
        
        Args:
            data_folder: 数据存储文件夹名称，默认在用户C盘创建
        """
        # 获取用户主目录（C:\Users\用户名）
        user_home = os.path.expanduser("~")
        # 在C盘根目录创建AgentData文件夹
        c_drive = os.path.splitdrive(user_home)[0]  # 获取C:
        self.data_folder = os.path.join(c_drive, os.sep, data_folder)
        
        # 确保数据文件夹存在
        try:
            os.makedirs(self.data_folder, exist_ok=True)
        except PermissionError:
            # 如果没有权限在C盘根目录创建，则在用户文档目录下创建
            documents_path = os.path.join(user_home, "Documents")
            self.data_folder = os.path.join(documents_path, data_folder)
            os.makedirs(self.data_folder, exist_ok=True)
        
        # 元数据文件路径
        self.metadata_file = os.path.join(self.data_folder, "metadata.json")
        self._init_metadata()
    
    def _init_metadata(self):
        """初始化元数据文件"""
        if not os.path.exists(self.metadata_file):
            metadata = {
                "conversations": {},
                "next_id": 1
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _load_metadata(self):
        """加载元数据"""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载元数据失败: {e}")
            self._init_metadata()
            return {"conversations": {}, "next_id": 1}
    
    def _save_metadata(self, metadata):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存元数据失败: {e}")
    
    def _get_conversation_file_path(self, conv_id, title=None):
        """获取对话文件路径，优先查找带标题的文件"""
        # 先尝试查找带标题的文件
        if title:
            safe_title = self._sanitize_filename(title)
            titled_path = os.path.join(self.data_folder, f"conversation_{conv_id}_{safe_title}.txt")
            if os.path.exists(titled_path):
                return titled_path
        
        # 查找所有匹配的文件
        import glob
        pattern = os.path.join(self.data_folder, f"conversation_{conv_id}*.txt")
        matches = glob.glob(pattern)
        
        if matches:
            # 如果有多个匹配，选择最新的
            latest_file = max(matches, key=os.path.getmtime)
            return latest_file
        
        # 回退到基本文件名
        return os.path.join(self.data_folder, f"conversation_{conv_id}.txt")
    
    def _rename_conversation_file(self, conv_id, old_title, new_title):
        """重命名对话文件为带标题的文件名"""
        try:
            # 获取当前文件路径
            current_path = self._get_conversation_file_path(conv_id, old_title)
            
            # 清理新文件名中的特殊字符
            safe_title = self._sanitize_filename(new_title)
            new_filename = f"conversation_{conv_id}_{safe_title}.txt"
            new_path = os.path.join(self.data_folder, new_filename)
            
            # 如果当前文件存在且新路径不同，重命名它
            if os.path.exists(current_path) and current_path != new_path:
                os.rename(current_path, new_path)
                print(f"文件已重命名: {os.path.basename(current_path)} -> {os.path.basename(new_path)}")
            
        except Exception as e:
            print(f"重命名文件失败: {e}")
    
    def _sanitize_filename(self, filename):
        """清理文件名，移除特殊字符"""
        import re
        # 移除或替换不允许的字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        return sanitized
    
    def create_new_conversation(self):
        """创建新对话，返回对话ID"""
        metadata = self._load_metadata()
        
        conv_id = str(metadata["next_id"])
        metadata["next_id"] += 1
        
        # 创建对话记录
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata["conversations"][conv_id] = {
            "title": "新对话",
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        # 保存元数据
        self._save_metadata(metadata)
        
        # 创建对话文件
        file_path = self._get_conversation_file_path(conv_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# 对话记录 - {timestamp}\n\n")
        
        return conv_id
    
    def delete_conversation(self, conv_id):
        """删除对话"""
        metadata = self._load_metadata()
        
        # 获取对话标题用于查找文件
        title = metadata["conversations"].get(conv_id, {}).get("title", "新对话")
        
        # 从元数据中删除
        if conv_id in metadata["conversations"]:
            del metadata["conversations"][conv_id]
            self._save_metadata(metadata)
        
        # 删除对话文件（使用增强的路径查找）
        file_path = self._get_conversation_file_path(conv_id, title)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"已删除对话文件: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"删除对话文件失败: {e}")
    
    def update_conversation_title(self, conv_id, new_title):
        """更新对话标题，并同步重命名txt文件"""
        metadata = self._load_metadata()
        
        if conv_id in metadata["conversations"]:
            old_title = metadata["conversations"][conv_id]["title"]
            
            # 更新元数据
            metadata["conversations"][conv_id]["title"] = new_title
            metadata["conversations"][conv_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_metadata(metadata)
            
            # 尝试重命名txt文件
            self._rename_conversation_file(conv_id, old_title, new_title)
    
    def add_message(self, conv_id, role, content):
        """添加消息到对话"""
        # 获取对话信息用于确定文件路径
        metadata = self._load_metadata()
        title = metadata["conversations"].get(conv_id, {}).get("title", "新对话")
        file_path = self._get_conversation_file_path(conv_id, title)
        
        # 更新元数据中的更新时间
        if conv_id in metadata["conversations"]:
            metadata["conversations"][conv_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_metadata(metadata)
        
        # 添加消息到文件
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role_name = "用户" if role == "user" else "AI助手"
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {role_name}:\n")
                f.write(f"{content}\n\n")
        except Exception as e:
            print(f"添加消息失败: {e}")
    
    def get_history(self, conv_id):
        """获取对话历史"""
        # 获取对话信息用于确定文件路径
        metadata = self._load_metadata()
        title = metadata["conversations"].get(conv_id, {}).get("title", "新对话")
        file_path = self._get_conversation_file_path(conv_id, title)
        
        if not os.path.exists(file_path):
            return []
        
        messages = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_message = None
            content_lines = []
            
            for line in lines:
                line = line.rstrip('\n')
                
                # 跳过标题行和空行
                if line.startswith('#') or not line.strip():
                    if current_message and content_lines:
                        current_message['content'] = '\n'.join(content_lines).strip()
                        messages.append(current_message)
                        current_message = None
                        content_lines = []
                    continue
                
                # 检查是否是新消息的开始
                if line.startswith('[') and '] ' in line and ('用户:' in line or 'AI助手:' in line):
                    # 保存上一条消息
                    if current_message and content_lines:
                        current_message['content'] = '\n'.join(content_lines).strip()
                        messages.append(current_message)
                    
                    # 开始新消息
                    if '用户:' in line:
                        role = 'user'
                    else:
                        role = 'assistant'
                    
                    current_message = {'role': role}
                    content_lines = []
                else:
                    # 消息内容行
                    if current_message:
                        content_lines.append(line)
            
            # 处理最后一条消息
            if current_message and content_lines:
                current_message['content'] = '\n'.join(content_lines).strip()
                messages.append(current_message)
                
        except Exception as e:
            print(f"读取对话历史失败: {e}")
            return []
        
        return messages
    
    def get_all_conversations(self):
        """获取所有对话列表"""
        metadata = self._load_metadata()
        conversations = []
        
        for conv_id, info in metadata["conversations"].items():
            conversations.append((
                conv_id,
                info["title"],
                info["updated_at"]
            ))
        
        # 按更新时间倒序排序
        conversations.sort(key=lambda x: x[2], reverse=True)
        return conversations
    
    def get_latest_conversation(self):
        """获取最新的对话"""
        conversations = self.get_all_conversations()
        return conversations[0] if conversations else None
    
    def clear_conversation_history(self, conv_id):
        """清空对话历史（保留对话，但清空消息）"""
        # 获取对话信息用于确定文件路径
        metadata = self._load_metadata()
        title = metadata["conversations"].get(conv_id, {}).get("title", "新对话")
        file_path = self._get_conversation_file_path(conv_id, title)
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# 对话记录 - {timestamp}\n\n")
            
            # 更新元数据
            if conv_id in metadata["conversations"]:
                metadata["conversations"][conv_id]["updated_at"] = timestamp
                self._save_metadata(metadata)
                
        except Exception as e:
            print(f"清空对话历史失败: {e}")
    
    def scan_and_rebuild_metadata(self):
        """扫描文件夹中的对话文件并重建元数据"""
        print(f"开始扫描文件夹: {self.data_folder}")
        
        if not os.path.exists(self.data_folder):
            print("数据文件夹不存在")
            return 0
        
        import glob
        import re
        
        # 查找所有对话文件
        pattern = os.path.join(self.data_folder, "conversation_*.txt")
        conversation_files = glob.glob(pattern)
        
        print(f"发现 {len(conversation_files)} 个对话文件")
        
        metadata = self._load_metadata()
        discovered_conversations = {}
        max_id = 0
        
        for file_path in conversation_files:
            try:
                filename = os.path.basename(file_path)
                
                # 解析文件名提取对话ID和标题
                match = re.match(r'conversation_(\d+)(?:_(.+))?\.txt', filename)
                if not match:
                    continue
                
                conv_id = match.group(1)
                title_from_filename = match.group(2) if match.group(2) else None
                
                # 如果文件名包含标题，使用它；否则尝试从文件内容获取
                if title_from_filename:
                    # 反向处理文件名清理
                    title = title_from_filename.replace('_', ' ')
                else:
                    title = self._extract_title_from_file(file_path) or "新对话"
                
                # 获取文件时间
                stat = os.stat(file_path)
                created_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                updated_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                discovered_conversations[conv_id] = {
                    "title": title,
                    "created_at": created_time,
                    "updated_at": updated_time
                }
                
                max_id = max(max_id, int(conv_id))
                print(f"发现对话: ID={conv_id}, 标题={title}")
                
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
        
        # 合并现有元数据和发现的对话
        for conv_id, info in discovered_conversations.items():
            if conv_id not in metadata["conversations"]:
                metadata["conversations"][conv_id] = info
            else:
                # 如果发现的标题更有意义，更新标题
                if info["title"] != "新对话" and metadata["conversations"][conv_id]["title"] == "新对话":
                    metadata["conversations"][conv_id]["title"] = info["title"]
        
        # 更新下一个ID
        metadata["next_id"] = max(metadata.get("next_id", 1), max_id + 1)
        
        # 保存更新的元数据
        self._save_metadata(metadata)
        print(f"元数据重建完成，总对话数: {len(metadata['conversations'])}")
        
        return len(discovered_conversations)
    
    def _extract_title_from_file(self, file_path):
        """从对话文件中提取有意义的标题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找第一条用户消息作为标题
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('[') and '用户:' in line:
                    # 找到下一行的内容
                    if i + 1 < len(lines):
                        content = lines[i + 1].strip()
                        if content and len(content) > 0:
                            # 截取前30个字符作为标题
                            title = content[:30]
                            if len(content) > 30:
                                title += "..."
                            return title
            
        except Exception as e:
            print(f"从文件提取标题失败: {e}")
        
        return None
        
    def refresh_conversations(self):
        """刷新对话列表，重新扫描文件夹"""
        count = self.scan_and_rebuild_metadata()
        print(f"刷新完成，发现 {count} 个对话文件")
        return self.get_all_conversations()
    
    def delete_message_by_index(self, conv_id, message_index):
        """删除指定索引的单条消息（文件存储实现）"""
        print(f"文件存储删除消息: 对话ID={conv_id}, 索引={message_index}")
        
        # 获取所有消息
        messages = self.get_history(conv_id)
        
        if not messages or message_index < 0 or message_index >= len(messages):
            print(f"消息索引无效: {message_index}")
            return
        
        # 删除指定索引的消息
        messages.pop(message_index)
        print(f"删除后剩余消息数: {len(messages)}")
        
        # 重写整个文件
        metadata = self._load_metadata()
        title = metadata["conversations"].get(conv_id, {}).get("title", "新对话")
        file_path = self._get_conversation_file_path(conv_id, title)
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# 对话记录 - {timestamp}\n\n")
                
                # 重新写入所有消息
                for message in messages:
                    role_name = "用户" if message['role'] == "user" else "AI助手"
                    f.write(f"[{timestamp}] {role_name}:\n")
                    f.write(f"{message['content']}\n\n")
            
            # 更新元数据
            if conv_id in metadata["conversations"]:
                metadata["conversations"][conv_id]["updated_at"] = timestamp
                self._save_metadata(metadata)
            
            print("文件存储删除消息完成")
                
        except Exception as e:
            print(f"删除消息失败: {e}")