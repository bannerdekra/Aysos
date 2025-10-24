#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转换旧格式（数组JSON）到新格式（JSONL）
"""

import json
import os

def convert_to_jsonl():
    """转换所有旧格式文件到JSONL格式"""
    
    data_dir = "C:\\AgentData"
    
    print("\n" + "="*70)
    print("数组JSON → JSONL 格式转换工具")
    print("="*70 + "\n")
    
    converted_count = 0
    
    for filename in os.listdir(data_dir):
        if not filename.startswith("conv_") or not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(data_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 检查是否是数组格式（旧格式）
            if not content.startswith('['):
                # 已经是 JSONL 格式
                continue
            
            print(f"📝 转换: {filename}")
            
            # 解析旧的数组格式
            try:
                messages = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"   ⚠️  解析失败: {e}")
                continue
            
            if not isinstance(messages, list):
                print(f"   ⚠️  不是数组格式，跳过")
                continue
            
            # 转换为JSONL格式
            with open(filepath, 'w', encoding='utf-8') as f:
                for msg in messages:
                    json.dump(msg, f, ensure_ascii=False)
                    f.write('\n')
            
            print(f"   ✅ 转换完成，{len(messages)} 条消息")
            converted_count += 1
            
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    print(f"\n{'='*70}")
    print(f"✅ 转换完成！共转换 {converted_count} 个文件")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    convert_to_jsonl()
