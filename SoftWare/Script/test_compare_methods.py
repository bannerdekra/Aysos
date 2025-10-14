"""
对比测试脚本 - 对比成功的测试脚本和实际应用的差异
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_method_1_creat_style():
    """方法 1: 使用 creat.py 的原始方式（已知成功）"""
    print("\n" + "=" * 70)
    print("方法 1: creat.py 原始方式（参考代码）")
    print("=" * 70)
    
    import requests
    import base64
    from PIL import Image
    import io
    
    API_URL = "http://127.0.0.1:7860"
    TXT2IMG_ENDPOINT = "/sdapi/v1/txt2img"
    
    # creat.py 的原始 PAYLOAD
    PAYLOAD = {
        "prompt": "masterpiece, best quality, 1girl, standing, long hair, blue eyes, white dress, beach, sky, clouds, sunlight",
        "negative_prompt": "lowres, deformed, jpeg artifacts, blurry, worst quality",
        "steps": 30,
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
    
    print("Payload:")
    print(json.dumps(PAYLOAD, indent=2))
    print(f"\n发送请求到: {API_URL}{TXT2IMG_ENDPOINT}")
    
    try:
        response = requests.post(
            url=f"{API_URL}{TXT2IMG_ENDPOINT}",
            json=PAYLOAD,
            timeout=60
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 方法 1 成功！")
            return True, PAYLOAD
        else:
            print(f"❌ 方法 1 失败！状态码: {response.status_code}")
            print(f"响应: {response.text[:300]}")
            return False, PAYLOAD
            
    except Exception as e:
        print(f"❌ 方法 1 异常: {e}")
        return False, PAYLOAD


def test_method_2_generator_class():
    """方法 2: 使用 ImageGenerator 类（应用中的方式）"""
    print("\n" + "=" * 70)
    print("方法 2: ImageGenerator 类方式（应用代码）")
    print("=" * 70)
    
    from image_generator import ImageGenerator
    
    generator = ImageGenerator()
    
    # 使用相同的提示词
    prompt = "masterpiece, best quality, 1girl, standing, long hair, blue eyes, white dress, beach, sky, clouds, sunlight"
    
    print(f"提示词: {prompt}")
    print("调用 generator.generate_image_with_progress()...")
    
    try:
        image_path, error = generator.generate_image_with_progress(prompt)
        
        if image_path:
            print(f"✅ 方法 2 成功！图片: {image_path}")
            return True
        else:
            print(f"❌ 方法 2 失败: {error}")
            return False
            
    except Exception as e:
        print(f"❌ 方法 2 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_method_3_with_ai_translation():
    """方法 3: 完整流程（AI翻译 + 生成）"""
    print("\n" + "=" * 70)
    print("方法 3: 完整流程（AI翻译 + ImageGenerator）")
    print("=" * 70)
    
    from image_generator import ImageGenerator
    from api_client import get_ai_reply
    
    generator = ImageGenerator()
    
    user_input = "一只可爱的猫咪在花园里"
    print(f"用户输入: {user_input}")
    
    # 步骤 1: AI 翻译
    print("\n步骤 1: AI 翻译提示词...")
    try:
        prompt = generator.translate_prompt_via_ai(user_input, get_ai_reply)
        print(f"AI 翻译结果: {prompt}")
        
        # 检查提示词
        if not prompt or len(prompt.strip()) < 5:
            print("❌ AI 翻译失败，提示词太短")
            return False
        
        # 检查是否有特殊字符
        print(f"提示词长度: {len(prompt)}")
        print(f"提示词类型: {type(prompt)}")
        print(f"提示词编码测试: {prompt.encode('utf-8')[:100]}")
        
    except Exception as e:
        print(f"❌ AI 翻译异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步骤 2: 生成图片
    print("\n步骤 2: 使用翻译后的提示词生成图片...")
    try:
        image_path, error = generator.generate_image_with_progress(prompt)
        
        if image_path:
            print(f"✅ 方法 3 成功！图片: {image_path}")
            return True
        else:
            print(f"❌ 方法 3 失败: {error}")
            return False
            
    except Exception as e:
        print(f"❌ 方法 3 生成异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_payloads():
    """对比不同方法的 payload 差异"""
    print("\n" + "=" * 70)
    print("🔍 Payload 对比分析")
    print("=" * 70)
    
    # 方法 1 的 payload（已知成功）
    payload_1 = {
        "prompt": "test prompt",
        "negative_prompt": "lowres, deformed",
        "steps": 30,
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
    
    # 方法 2 的 default_params
    from image_generator import ImageGenerator
    generator = ImageGenerator()
    payload_2 = generator.default_params.copy()
    payload_2["prompt"] = "test prompt"
    
    print("\n方法 1 (creat.py) 的键:")
    print(sorted(payload_1.keys()))
    
    print("\n方法 2 (ImageGenerator) 的键:")
    print(sorted(payload_2.keys()))
    
    # 找出差异
    keys_1 = set(payload_1.keys())
    keys_2 = set(payload_2.keys())
    
    only_in_1 = keys_1 - keys_2
    only_in_2 = keys_2 - keys_1
    common = keys_1 & keys_2
    
    if only_in_1:
        print(f"\n⚠️  只在方法1中的键: {only_in_1}")
    
    if only_in_2:
        print(f"\n⚠️  只在方法2中的键: {only_in_2}")
    
    print(f"\n共同的键: {len(common)} 个")
    
    # 对比值差异
    print("\n值的差异:")
    for key in common:
        if key == "prompt":
            continue
        if payload_1.get(key) != payload_2.get(key):
            print(f"  {key}:")
            print(f"    方法1: {payload_1[key]}")
            print(f"    方法2: {payload_2[key]}")


def check_sd_webui_logs():
    """提示用户检查 SD WebUI 日志"""
    print("\n" + "=" * 70)
    print("💡 调试建议")
    print("=" * 70)
    
    print("\n如果某个方法失败，请：")
    print("  1. 查看 SD WebUI 控制台的完整错误信息")
    print("  2. 检查 SD WebUI 版本和 API 兼容性")
    print("  3. 确认模型文件 'v1-5-pruned-emaonly' 是否存在")
    print("     （如果不存在，SD 会使用当前加载的模型）")
    print("  4. 尝试在 WebUI 界面手动生成图片确认功能正常")
    print()
    print("查看详细调试输出：")
    print("  - 在上面的输出中找 [DEBUG] 标记的行")
    print("  - 对比成功和失败时的 payload 差异")
    print()


def main():
    """主测试流程"""
    print("\n🔍 对比测试脚本 - 诊断 502 错误")
    print("=" * 70)
    
    results = {}
    
    # 对比 payload 结构
    compare_payloads()
    
    # 测试方法 1：原始方式
    success_1, payload_1 = test_method_1_creat_style()
    results['方法1_原始'] = success_1
    
    # 测试方法 2：ImageGenerator
    success_2 = test_method_2_generator_class()
    results['方法2_类方式'] = success_2
    
    # 测试方法 3：完整流程
    success_3 = test_method_3_with_ai_translation()
    results['方法3_完整流程'] = success_3
    
    # 总结
    print("\n" + "=" * 70)
    print("📊 测试结果总结")
    print("=" * 70)
    
    for method, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {method}: {status}")
    
    # 分析
    print("\n🔍 问题分析:")
    if all(results.values()):
        print("  ✅ 所有方法都成功！问题可能在其他地方")
        print("     - 检查是否是并发请求导致的")
        print("     - 检查是否是线程安全问题")
    elif results['方法1_原始'] and not results['方法2_类方式']:
        print("  ⚠️  原始方式成功，但类方式失败")
        print("     - 问题在 ImageGenerator 类的实现")
        print("     - 检查 default_params 和实际发送的 payload")
    elif results['方法2_类方式'] and not results['方法3_完整流程']:
        print("  ⚠️  类方式成功，但完整流程失败")
        print("     - 问题在 AI 翻译后的提示词")
        print("     - 检查提示词是否有特殊字符或格式问题")
    else:
        print("  ❌ 多个方法失败，检查 SD WebUI 状态")
    
    # 调试建议
    check_sd_webui_logs()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
