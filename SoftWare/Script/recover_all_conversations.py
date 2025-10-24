#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复所有对话元数据
从磁盘上的对话文件恢复元数据信息
"""

import os
import json
import re
from datetime import datetime

def recover_all_conversations():
    """从磁盘文件恢复所有对话元数据"""
    
    data_dir = "C:\\AgentData"
    metadata_file = os.path.join(data_dir, "metadata.json")
    
    print("\n" + "="*70)
    print("对话元数据恢复工具")
    print("="*70 + "\n")
    
    # 1. 扫描所有对话文件
    print("📂 正在扫描对话文件...")
    conversations = {}
    max_id = 0
    
    for filename in os.listdir(data_dir):
        if not filename.startswith("conv_") or not filename.endswith(".txt"):
            continue
        
        # 提取对话ID和标题
        # 格式: conv_[ID]_[TITLE].txt
        match = re.match(r"conv_(\d+)_(.+)\.txt$", filename)
        if not match:
            print(f"⚠️  文件格式不匹配: {filename}")
            continue
        
        conv_id = match.group(1)
        title = match.group(2)
        file_path = os.path.join(data_dir, filename)
        
        # 获取文件修改时间
        mtime = os.path.getmtime(file_path)
        updated_at = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        # 统计消息数
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                message_count = len(lines)
        except:
            message_count = 0
        
        conversations[conv_id] = {
            "title": title,
            "created_at": updated_at,
            "updated_at": updated_at,
            "message_count": message_count
        }
        
        max_id = max(max_id, int(conv_id))
        
        print(f"✅ {filename}")
        print(f"   ID={conv_id}, 标题={title}, 消息数={message_count}")
    
    if not conversations:
        print("❌ 没有找到任何对话文件")
        return
    
    # 2. 创建新的元数据
    print(f"\n💾 生成新的元数据文件...")
    metadata = {
        "conversations": conversations,
        "next_id": max_id + 1
    }
    
    # 3. 备份旧的元数据
    if os.path.exists(metadata_file):
        backup_file = metadata_file + ".backup"
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                old_metadata = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(old_metadata, f, ensure_ascii=False, indent=2)
            print(f"✅ 旧元数据已备份: {backup_file}")
        except:
            pass
    
    # 4. 写入新的元数据
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"✅ 新元数据已写入: {metadata_file}")
    except Exception as e:
        print(f"❌ 写入元数据失败: {e}")
        return
    
    # 5. 验证恢复结果
    print(f"\n" + "="*70)
    print("恢复结果验证")
    print("="*70 + "\n")
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        recovered_metadata = json.load(f)
    
    total_conversations = len(recovered_metadata["conversations"])
    total_messages = sum(conv.get("message_count", 0) for conv in recovered_metadata["conversations"].values())
    
    print(f"✅ 恢复成功！")
    print(f"   总对话数: {total_conversations}")
    print(f"   总消息数: {total_messages}")
    print(f"   下一个对话ID: {recovered_metadata['next_id']}")
    
    print(f"\n对话列表:")
    for conv_id in sorted(recovered_metadata["conversations"].keys(), key=lambda x: int(x)):
        conv = recovered_metadata["conversations"][conv_id]
        print(f"   [{conv_id}] {conv['title']} ({conv.get('message_count', 0)} 条消息)")
    
    print(f"\n" + "="*70)
    print("✅ 所有对话已恢复！现在启动应用时应该能看到所有对话")
    print("="*70 + "\n")

if __name__ == "__main__":
    recover_all_conversations()
