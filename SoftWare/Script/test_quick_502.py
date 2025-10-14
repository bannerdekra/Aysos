"""
快速测试脚本 - 跳过 AI 翻译，直接测试生成
专门用于验证 502 错误是否由提示词长度引起
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_different_prompts():
    """测试不同的提示词"""
    from image_generator import ImageGenerator
    
    generator = ImageGenerator()
    
    test_cases = [
        {
            "name": "短提示词(107字符) - 已知成功",
            "prompt": "masterpiece, best quality, 1girl, standing, long hair, blue eyes, white dress, beach, sky, clouds, sunlight"
        },
        {
            "name": "AI风格提示词(174字符) - 之前502",
            "prompt": "masterpiece, best quality, ultra-detailed, an adorable cat, cute feline, in a lush garden, surrounded by colorful flowers, vibrant greenery, natural lighting, highly detailed"
        },
        {
            "name": "简化版(120字符)",
            "prompt": "masterpiece, best quality, an adorable cat, in a lush garden, colorful flowers, natural lighting, detailed"
        }
    ]
    
    print("\n" + "=" * 70)
    print("快速测试 - 不同长度提示词对比")
    print("=" * 70)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        prompt = test_case["prompt"]
        
        print(f"\n【测试 {i}】{name}")
        print(f"长度: {len(prompt)} 字符")
        print(f"提示词: {prompt[:80]}...")
        
        try:
            print("生成中...")
            image_path, error = generator.generate_image_with_progress(prompt)
            
            if image_path:
                print(f"✅ 成功: {image_path}")
                results.append((name, len(prompt), "✅"))
            else:
                print(f"❌ 失败: {error}")
                results.append((name, len(prompt), f"❌ {error[:30]}"))
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append((name, len(prompt), f"❌ 异常"))
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    for name, length, result in results:
        print(f"{length:3}字符 - {result} - {name}")
    
    # 分析
    print("\n🔍 分析:")
    if all("✅" in r for _, _, r in results):
        print("  ✅ 所有提示词都成功！")
        print("  💡 问题已修复，或者不在提示词本身")
    else:
        failed = [(n, l) for n, l, r in results if "❌" in r]
        if failed:
            print(f"  ❌ 失败的提示词: {[f[1] for f in failed]} 字符")
            if 174 in [f[1] for f in failed]:
                print("  💡 确认：174字符的提示词仍然导致 502")
                print("  🔧 建议：限制 AI 翻译输出到 120 字符以内")


def main():
    """主函数"""
    print("🚀 快速测试 - 502 错误诊断（无 AI 调用）")
    
    # 检查连接
    from image_generator import ImageGenerator
    generator = ImageGenerator()
    
    print("\n检查 SD WebUI 连接...")
    success, message = generator.check_connection()
    
    if not success:
        print(f"❌ {message}")
        print("请确保 SD WebUI 已启动")
        return
    
    print(f"✅ {message}")
    
    # 运行测试
    test_different_prompts()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    
    print("\n💡 下一步:")
    print("  1. 如果所有测试都成功 → 问题已修复")
    print("  2. 如果174字符失败 → 需要限制 AI 输出长度")
    print("  3. 运行主程序测试完整流程")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
