# 版本号 V1.0.2
# Agent 项目

这是一个包含开发工具的个人助手项目，支持 Deepseek、Gemini 等多模型，自动代理穿透防火墙，气泡布局自适应。

# 开发准则（暂）

1.所有代码操作都必须写进日志文件夹 LOG（每日或每提交写一次），撰写LOG格式：时间+进度+其他（比如接下来的工作的实现方向，可不写）
LOG 例子：
2025.9.27
（1）.实现功能深色模式
（2）.实现根据系统时间自动切换深色模式
其他：讨论添加新功能

2.所有代码新添加的功能脚本都需要在 README-项目结构 中写明作用（每日或每提交写一次）
3.使用文本开发工具撰写提示词，该工具有存档方便溯源（开发者本地保存）
4.有任何新方向均需要完成以下完整的开发链条：提出idea——阐述目的——讨论必要性——论述可行性（技术路线）——执行改动
5.无论是否完成开发工作每日必须存档提交，github库的存档是可以选择性删除的只是一个保存平台，方便取用最新的开发版本
6.不允许同时编辑项目！！！需沟通协商各自的开发时间，确保每一时刻只有一个人在编辑该项目，每次编辑开始时都应该pull或者clone仓库再开始开发，确保项目进度统一

## 项目结构（2025-09-30）

- `SoftWare/Script/` - 所有脚本文件
  - `main.py` - 主程序
  - `api_client.py` - AI API调用（支持 Gemini/DeepSeek，官方SDK集成）
  - `api_config.py` - API配置与自动代理设置
  - `chat_area.py` - 聊天区域，气泡布局优化，支持气泡删除
  - `bubble_copy_handler.py` - 对话气泡复制与删除信号
  - `chat_ui.py` - 聊天界面UI
  - `database_manager.py` - 数据库/DSN管理
  - `dialogs.py` - 软件弹窗类
  - `file_manager.py` - 本地对话管理，支持消息删除
  - `gemini_context_manager.py` - Gemini上下文与文件上传管理，统一走 File API，限定 PDF/JPG/PNG
  - `input_bar.py` - 输入栏
  - `responsive_switch.py` - 响应式切换
  - `sidebar.py` - 任务管理栏
  - `storage_config.py` - DSN逻辑切换，支持文件存储删除
  - `test_attachment_recognition.py` - 附件识别测试
  - `theme_manager.py` - 主题管理
  - `theme_settings.json` - 主题配置
- `SoftWare/Image/` - 软件资源
  - `Backgroud/` - UI背景图片
  - `loading/` - Agent回答加载中GIF
- `SoftWare/Icon/` - 软件封装图标
- `TOOL/` - 开发工具与辅助脚本
  - `dev_notebook.py` - 开发记事本工具
  - `sentence/summary.md` - 更新内容摘要
  - `test_fixes.py` - 自动化修复测试
  - `test_file_upload.py` - 附件上传测试
- `LOG/` - 日志与说明
  - `UPDATE_2025-09-28.md`/`UPDATE_2025-09-30.md`/`UPDATE_2025-10-05.md`/`UPDATE_2025-10-08.md` - 每日更新日志
  - `README.md` - 发布说明

## 功能特性（2025-10-05）

- 支持多AI模型（Gemini/DeepSeek），可随时切换
- Gemini集成官方SDK，自动密钥管理，支持最新模型（gemini-2.5-flash）
- 聊天气泡自适应布局，内容包裹优先，最大宽度限制，换行撑满
- 自动代理配置，支持本地代理穿透防火墙
- 完善的配置诊断与修复脚本
- 详细的技术文档与更新日志
- 联网即可使用个人助手问答
- 本地保存对话记录不泄密
- 预设提示词提高问答效率
- 任务管理栏滚动播放任务名称
- UI界面可缩放至任意大小
- **高级文本搜索功能**（2025-10-05 新增）
  - 支持当前对话搜索和全局搜索
  - 智能高亮显示：气泡背景高亮 + 关键词文本高亮（双重高亮）
  - 搜索结果计数与导航："已查找到 X 处内容，现在显示的是 Y/X 处"
  - 上一处/下一处快速导航按钮（找到2处及以上时自动显示）
  - Ctrl+F 快捷键快速唤醒搜索对话框
  - 搜索结果自动居中显示，3秒高亮后恢复
  - 支持大小写不敏感匹配

## 未来开发计划：
- 加入其他模型，目前已接入Gemini和DeepSeek
- 接入附件处理功能（现无法实现上传附件，仅在UI中增加上传按钮）