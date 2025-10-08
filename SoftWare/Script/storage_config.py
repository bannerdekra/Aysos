import os
import json
from typing import Optional, List, Dict, Union
from database_manager import DatabaseManager
from file_manager import FileManager

class StorageConfig:
    """存储配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        # 获取程序根目录
        current_file = os.path.dirname(os.path.abspath(__file__))
        self.root_path = os.path.dirname(os.path.dirname(current_file))
        self.config_file = os.path.join(self.root_path, "storage_config.json")
        
        # 默认配置
        self.default_config = {
            "storage_type": "file",  # "file" 或 "dsn"
            "dsn_name": "",
            "last_migration": None
        }
        
        self.config = self._load_config()
        
        # 初始化存储管理器
        self.file_manager = FileManager()
        self.db_manager = None
        
        if self.config["storage_type"] == "dsn" and self.config["dsn_name"]:
            try:
                self.db_manager = DatabaseManager(self.config["dsn_name"])
            except Exception as e:
                print(f"DSN连接失败，切换到文件存储: {e}")
                self._fallback_to_file()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        
        return self.default_config.copy()
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _fallback_to_file(self):
        """回退到文件存储"""
        self.config["storage_type"] = "file"
        self.config["dsn_name"] = ""
        self.db_manager = None
        self._save_config()
    
    def get_current_storage_type(self):
        """获取当前存储类型"""
        return self.config["storage_type"]
    
    def get_current_dsn(self):
        """获取当前DSN名称"""
        return self.config["dsn_name"]

    def test_dsn_connection(self, dsn_name):
        """测试DSN连接"""
        success, message = DatabaseManager.test_dsn_connection(dsn_name)
        return success

    def migrate_data(self):
        """迁移数据"""
        if self.config["storage_type"] == "file":
            # 从数据库迁移到文件
            return self._migrate_dsn_to_file()
        else:
            # 从文件迁移到数据库
            return self._migrate_file_to_dsn()
    
    def switch_to_file_storage(self):
        """切换到文件存储"""
        print("切换到文件存储...")
        
        # 如果当前是DSN存储，需要迁移数据
        if self.config["storage_type"] == "dsn" and self.db_manager:
            self._migrate_dsn_to_file()
        
        # 更新配置
        self.config["storage_type"] = "file"
        self.config["dsn_name"] = ""
        self.db_manager = None
        self._save_config()
        
        print("已切换到文件存储")
    
    def switch_to_dsn_storage(self, dsn_name):
        """切换到DSN存储"""
        print(f"切换到DSN存储: {dsn_name}")
        
        # 测试DSN连接
        success, message = DatabaseManager.test_dsn_connection(dsn_name)
        if not success:
            raise Exception(f"DSN连接失败: {message}")
        
        # 如果当前是文件存储，需要迁移数据
        if self.config["storage_type"] == "file":
            # 先创建数据库管理器
            self.db_manager = DatabaseManager(dsn_name)
            self._migrate_file_to_dsn()
        else:
            # 如果已经是DSN存储，只是更换DSN
            if self.db_manager:
                self.db_manager.close()
            self.db_manager = DatabaseManager(dsn_name)
        
        # 更新配置
        self.config["storage_type"] = "dsn"
        self.config["dsn_name"] = dsn_name
        self._save_config()
        
        print("已切换到DSN存储")
    
    def _migrate_file_to_dsn(self):
        """从文件存储迁移到DSN存储"""
        print("正在迁移数据：文件 -> DSN...")
        
        # 获取所有文件中的对话
        conversations = self.file_manager.get_all_conversations()
        
        for conv_id, title, updated_at in conversations:
            # 在数据库中创建对话
            new_conv_id = self.db_manager.create_new_conversation(title)
            
            # 获取文件中的历史消息
            messages = self.file_manager.get_history(conv_id)
            
            # 将消息添加到数据库
            for message in messages:
                self.db_manager.add_message(new_conv_id, message['role'], message['content'])
            
            print(f"迁移对话: {title} ({len(messages)}条消息)")
        
        print(f"数据迁移完成：共迁移{len(conversations)}个对话")
    
    def _migrate_dsn_to_file(self):
        """从DSN存储迁移到文件存储"""
        print("正在迁移数据：DSN -> 文件...")
        
        # 获取数据库中的所有对话
        conversations = self.db_manager.get_all_conversations()
        
        for conv_data in conversations:
            conv_id = conv_data[0]
            title = conv_data[1]
            
            # 在文件管理器中创建新对话
            new_conv_id = self.file_manager.create_new_conversation()
            self.file_manager.update_conversation_title(new_conv_id, title)
            
            # 获取数据库中的历史消息
            messages = self.db_manager.get_history(conv_id)
            
            # 将消息添加到文件
            for message in messages:
                self.file_manager.add_message(new_conv_id, message['role'], message['content'])
            
            print(f"迁移对话: {title} ({len(messages)}条消息)")
        
        print(f"数据迁移完成：共迁移{len(conversations)}个对话")
    
    # 统一接口方法
    def get_manager(self):
        """获取当前的存储管理器"""
        if self.config["storage_type"] == "dsn" and self.db_manager:
            return self.db_manager
        else:
            return self.file_manager
    
    def create_new_conversation(self):
        """创建新对话"""
        return self.get_manager().create_new_conversation()
    
    def delete_conversation(self, conv_id):
        """删除对话"""
        return self.get_manager().delete_conversation(conv_id)
    
    def update_conversation_title(self, conv_id, new_title):
        """更新对话标题"""
        return self.get_manager().update_conversation_title(conv_id, new_title)
    
    def add_message(self, conv_id, role, content):
        """添加消息"""
        return self.get_manager().add_message(conv_id, role, content)
    
    def get_history(self, conv_id):
        """获取对话历史"""
        return self.get_manager().get_history(conv_id)
    
    def get_all_conversations(self):
        """获取所有对话"""
        return self.get_manager().get_all_conversations()
    
    def get_latest_conversation(self):
        """获取最新对话"""
        return self.get_manager().get_latest_conversation()
    
    def delete_messages_from_index(self, conv_id, start_index):
        """删除从指定索引开始的所有消息（仅数据库管理器支持）"""
        if self.config["storage_type"] == "dsn" and self.db_manager:
            return self.db_manager.delete_messages_from_index(conv_id, start_index)
        else:
            # 文件管理器不支持此操作，需要重写整个文件
            if hasattr(self.file_manager, "delete_messages_from_index"):
                return self.file_manager.delete_messages_from_index(conv_id, start_index)
            print("文件存储暂不支持从指定索引删除消息")
    
    def delete_message_by_index(self, conv_id, message_index):
        """删除指定索引的消息（仅数据库管理器支持）"""
        if self.config["storage_type"] == "dsn" and self.db_manager:
            return self.db_manager.delete_message_by_index(conv_id, message_index)
        else:
            if hasattr(self.file_manager, "delete_message_by_index"):
                return self.file_manager.delete_message_by_index(conv_id, message_index)
            print("文件存储暂不支持删除指定索引的消息")
    
    def clear_conversation_history(self, conv_id):
        """清空对话历史"""
        if self.config["storage_type"] == "dsn" and self.db_manager:
            # 删除所有消息但保留对话
            self.db_manager.cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conv_id,))
            self.db_manager.conn.commit()
        else:
            # 文件管理器的清空方法
            self.file_manager.clear_conversation_history(conv_id)
    
    def close(self):
        """关闭连接"""
        if self.db_manager:
            self.db_manager.close()