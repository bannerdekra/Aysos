"""
专门测试 AI 翻译后提示词的问题
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prompt_length_issue():
    """测试不同长度的提示词"""
    import requests
    
    API_URL = "http://127.0.0.1:7860"
    TXT2IMG_ENDPOINT = "/sdapi/v1/txt2img"
    
    test_cases = [
        {
            "name": "短提示词(100字符)",
            "prompt": "masterpiece, best quality, 1girl, standing, long hair, blue eyes, white dress, beach, sky, clouds, sunlight"
        },
        {
            "name": "中等提示词(150字符)", 
            "prompt": "masterpiece, best quality, ultra-detailed, an adorable cat, cute feline, in a lush garden, surrounded by colorful flowers, vibrant greenery, natural lighting"
        },
        {
            "name": "长提示词(174字符 - 之前失败的)",
            "prompt": "masterpiece, best quality, ultra-detailed, an adorable cat, cute feline, in a lush garden, surrounded by colorful flowers, vibrant greenery, natural lighting, highly detailed"
        },
        {
            "name": "超长提示词(250+字符)",
            "prompt": "masterpiece, best quality, ultra-detailed, highly detailed, extremely detailed, professional photography, 8k resolution, an adorable cat, cute feline, soft fur, bright eyes, in a lush garden, surrounded by colorful flowers, vibrant greenery, natural lighting, soft shadows, bokeh background, sharp focus"
        }
    ]
    
    print("\n" + "=" * 70)
    print("测试不同长度提示词对 SD WebUI 的影响")
    print("=" * 70)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        prompt = test_case["prompt"]
        
        print(f"\n测试 {i}: {name}")
        print(f"提示词长度: {len(prompt)} 字符")
        print(f"提示词: {prompt[:80]}...")
        
        payload = {
            "prompt": prompt,
            "negative_prompt": "lowres, deformed, jpeg artifacts, blurry, worst quality",
            "steps": 20,  # 减少步数加快测试
            "sampler_name": "DPM++ 2M Karras",
            "cfg_scale": 7.0,
            "seed": -1,
            "width": 512,
            "height": 512,
            "n_iter": 1,
            "batch_size": 1,
            "override_settings": {
                "sd_model_checkpoint": "v1-5-pruned-emaonly"
            }
        }
        
        try:
            response = requests.post(
                url=f"{API_URL}{TXT2IMG_ENDPOINT}",
                json=payload,
                timeout=60
            )
            
            status = response.status_code
            print(f"响应状态码: {status}")
            
            if status == 200:
                print("✅ 成功")
                results.append((name, len(prompt), "✅"))
            else:
                print(f"❌ 失败 - 状态码 {status}")
                print(f"响应内容: {response.text[:200]}")
                results.append((name, len(prompt), f"❌ {status}"))
                
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append((name, len(prompt), f"❌ 异常"))
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    for name, length, result in results:
        print(f"{name:30} ({length:3}字符): {result}")
    
    # 分析
    print("\n分析:")
    success_count = sum(1 for _, _, r in results if r == "✅")
    if success_count == len(results):
        print("  ✅ 所有长度的提示词都成功")
        print("  💡 问题不在提示词长度")
    else:
        # 找出失败的长度阈值
        failed_lengths = [length for _, length, r in results if r != "✅"]
        if failed_lengths:
            print(f"  ⚠️  失败的提示词长度: {failed_lengths}")
            print(f"  💡 建议限制提示词长度在 {min(failed_lengths)-10} 字符以内")


def test_special_characters():
    """测试特殊字符是否导致问题"""
    import requests
    
    API_URL = "http://127.0.0.1:7860"
    TXT2IMG_ENDPOINT = "/sdapi/v1/txt2img"
    
    test_cases = [
        {
            "name": "正常提示词",
            "prompt": "masterpiece, best quality, 1girl, blue eyes"
        },
        {
            "name": "带引号",
            "prompt": 'masterpiece, "best quality", 1girl, blue eyes'
        },
        {
            "name": "带特殊标点",
            "prompt": "masterpiece, best quality! 1girl? blue eyes..."
        },
        {
            "name": "带括号",
            "prompt": "masterpiece, best quality, (1girl), [blue eyes]"
        }
    ]
    
    print("\n" + "=" * 70)
    print("测试特殊字符对 SD WebUI 的影响")
    print("=" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        prompt = test_case["prompt"]
        
        print(f"\n测试 {i}: {name}")
        print(f"提示词: {prompt}")
        
        payload = {
            "prompt": prompt,
            "negative_prompt": "lowres",
            "steps": 10,  # 最少步数快速测试
            "sampler_name": "DPM++ 2M Karras",
            "cfg_scale": 7.0,
            "seed": -1,
            "width": 512,
            "height": 512,
            "n_iter": 1,
            "batch_size": 1
        }
        
        try:
            response = requests.post(
                url=f"{API_URL}{TXT2IMG_ENDPOINT}",
                json=payload,
                timeout=60
            )
            
            status = response.status_code
            
            if status == 200:
                print("✅ 成功")
            else:
                print(f"❌ 失败 - 状态码 {status}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")


def test_ai_translated_prompt():
    """测试实际 AI 翻译的提示词"""
    print("\n" + "=" * 70)
    print("测试实际 AI 翻译后的提示词")
    print("=" * 70)
    
    from image_generator import ImageGenerator
    from api_client import get_ai_reply
    
    generator = ImageGenerator()
    
    test_descriptions = [
        "一只可爱的猫咪在花园里",
        "美丽的女孩在海边看日落",
        "科幻未来城市"
    ]
    
    for desc in test_descriptions:
        print(f"\n用户输入: {desc}")
        
        # AI 翻译
        prompt = generator.translate_prompt_via_ai(desc, get_ai_reply)
        
        print(f"翻译结果: {prompt}")
        print(f"长度: {len(prompt)} 字符")
        
        # 测试生成
        print("测试生成...")
        image_path, error = generator.generate_image_with_progress(prompt)
        
        if image_path:
            print(f"✅ 成功: {image_path}")
        else:
            print(f"❌ 失败: {error}")


def main():
    """主测试"""
    print("🔍 专项测试 - AI 翻译提示词问题诊断")
    
    # 测试 1: 不同长度
    test_prompt_length_issue()
    
    # 测试 2: 特殊字符
    test_special_characters()
    
    # 测试 3: 实际 AI 翻译
    print("\n" + "=" * 70)
    user_choice = input("\n是否测试实际 AI 翻译？(y/n): ")
    if user_choice.lower() == 'y':
        test_ai_translated_prompt()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
