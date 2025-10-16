# 版本号 V1.0.8
# Agent 项目

这是一个包含开发工具的个人助手项目，支持 Deepseek、Gemini 等多模型，自动代理穿透防火墙，气泡布局自适应，支持多模态文件上传（图片、PDF、视频），集成 Stable Diffusion 本地绘画功能，**新增 LLM Function Calling 框架，支持动态调用外部工具（如百度搜索）获取实时信息**。

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

## 项目结构（2025-10-16）

- `SoftWare/Script/` - 所有脚本文件
  - `main.py` - 主程序
  - `api_client.py` - AI API调用（支持 Gemini/DeepSeek，官方SDK集成，**Function Calling 支持**）
  - `api_config.py` - API配置与自动代理设置
  - `model_registry.py` - **[2025-10-16]** AI模型统一配置中心（DeepSeek、Gemini、Claude、GPT-4o预置）
  - `baidu_searcher.py` - **[2025-10-16 新增]** 百度千帆搜索工具封装（270行）
  - `tool_executor.py` - **[2025-10-16 新增]** 通用工具执行器和注册管理（280行）
  - `chat_area.py` - 聊天区域，气泡布局优化，支持气泡删除，文件引用显示，SD生成进度实时显示
  - `bubble_copy_handler.py` - 对话气泡复制与删除信号
  - `chat_ui.py` - 聊天界面UI
  - `database_manager.py` - 数据库/DSN管理
  - `dialogs.py` - 软件弹窗类，文件上传模式提示增强
  - `file_manager.py` - 本地对话管理，支持消息删除
  - `gemini_context_manager.py` - Gemini上下文与文件上传管理，支持视频理解，仅限图片/PDF/视频
  - `input_bar.py` - 输入栏，支持多模态文件上传，SD生图触发
  - `image_generator.py` - Stable Diffusion 图像生成管理器
  - `creation_panel.py` - SD创作控制面板（动态单词计数，参数持久化）
  - `sd_config.py` - **[2025-10-16]** SD参数持久化配置管理
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
  - `test_function_calling.py` - **[2025-10-16 新增]** Function Calling 测试套件（260行）
  - `sentence/summary.md` - 更新内容摘要
  - `test_fixes.py` - 自动化修复测试
  - `test_file_upload.py` - 附件上传测试
- `LOG/` - 日志与说明
  - `UPDATE_2025-09-28.md` / `UPDATE_2025-09-30.md` / `UPDATE_2025-10-05.md` / `UPDATE_2025-10-08.md` / `UPDATE_2025-10-09.md` / `UPDATE_2025-10-10.md` / `UPDATE_2025-10-11.md` / `UPDATE_2025-10-15.md` / `UPDATE_2025-10-16.md` - 每日更新日志
  - `README.md` - 发布说明
- `UPDATE_2025-10-16_function_calling.md` - **[新增]** Function Calling 功能详细文档
- `GEMINI_VIDEO_SUPPORT.md` - Gemini 视频理解功能文档
- `test_video_support.py` - 视频支持测试套件

## 功能特性（2025-10-16）

### 🆕 LLM Function Calling（2025-10-16 重大更新）
- **🤖 智能工具调用**：AI 自动判断何时需要调用外部工具
  - 🔍 **百度搜索**：获取实时网络信息，支持最新资讯、技术文档查询
    - 🆕 **时效性过滤**: `search_recency_filter` (day/week/month/year) - 确保信息时效性
    - 🆕 **网站限定**: `site_filter` - 限定权威网站，提高准确性
    - 💡 组合使用高级参数，显著提升天气、新闻等实时信息查询的准确率
  - 📊 AI 自动决策：无需手动触发，根据问题内容智能选择工具和参数
  - 🔄 两步走循环：LLM 决策 → 工具执行 → 上下文注入 → 最终答案
- **⚡ 多模型支持**：
  - ✅ DeepSeek：完整 Function Calling 支持
  - ✅ Gemini：完整 Function Calling 支持（格式适配）
  - ✅ OpenAI Compatible API：通用支持
- **🔧 可扩展架构**：
  - 工具注册表模式，轻松添加新工具（天气、计算器等）
  - 标准 JSON Schema 定义，兼容 OpenAI 规范
  - 自动 JSON 序列化和错误处理
- **📝 使用示例**：
  ```python
  # 用户: "请搜索最新的 Python 3.13 新特性"
  # AI 自动调用百度搜索 → 获取结果 → 生成准确回答
  response = get_ai_reply(messages, provider='deepseek', enable_tools=True)
  ```
- **环境配置**：
  ```powershell
  # 设置百度千帆 API Key
  $env:BAIDU_SEARCH_APIKEY = "your_api_key_here"
  ```
- **详细文档**：
  - Function Calling 框架: `UPDATE_2025-10-16_function_calling.md`
  - 高级参数使用: `BAIDU_SEARCHER_ADVANCED_PARAMS.md` 🆕

### 核心功能
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

### Stable Diffusion 本地绘画（2025-10-15/16 重大更新）
- **🎨 创作控制面板**：完整的参数调整界面
  - 采样器、调度器、步数、CFG（支持0.5精度）、种子、宽/高等
  - 动态单词计数（xx/75），超限颜色预警
  - 模型自动刷新与切换
  - 参数自动持久化，下次启动加载
- **⚡ 实时进度反馈**：
  - 🔌 连接 SD WebUI
  - 📝 正在生成提示词
  - 🎨 正在生成图片（带百分比）
  - 渐变背景+边框+图标，消除等待焦虑
- **🚀 快速生成模式**：直接输入描述即可生成
- **🔧 代理绕过**：修复全局代理导致的502错误

### 多模态文件支持（2025-10-10/16 更新）
- **📸 图片支持**：JPEG, PNG, GIF, WebP, HEIC, HEIF
  - < 20MB：内嵌上传（快速响应）
  - ≥ 20MB：File API 上传（服务器保留48小时）
- **📄 PDF支持**：完整的PDF文档理解
  - < 20MB：内嵌上传
  - ≥ 20MB：File API 上传
- **🎬 视频支持**：MP4, MOV, MPEG, AVI, WebM
  - 所有视频强制使用 File API（无论大小）
  - 最大支持 2GB 视频文件
  - 服务器保留48小时，支持多轮对话引用
- **文件引用显示**：用户/Agent气泡底部显示附件文件名
- **双重验证**：扩展名 + MIME类型白名单双重检查
- **智能路由**：根据文件类型和大小自动选择最优上传方式
- **时效性提示**：上传时明确显示"仅单次对话"或"仅保存48小时"

### 高级文本搜索功能（2025-10-05）
- 支持当前对话搜索和全局搜索
- 智能高亮显示：气泡背景高亮 + 关键词文本高亮（双重高亮）
- 搜索结果计数与导航："已查找到 X 处内容，现在显示的是 Y/X 处"
- 上一处/下一处快速导航按钮（找到2处及以上时自动显示）
- Ctrl+F 快捷键快速唤醒搜索对话框
- 搜索结果自动居中显示，3秒高亮后恢复
- 支持大小写不敏感匹配

## 未来开发计划

### 短期计划
- 集成model_registry.py到API客户端
- 为Claude、GPT-4o实现完整API调用逻辑
- SD参数预设功能（保存/加载多套常用参数）
- 进度条可视化（替代文字百分比）
- 优化视频文件的上传进度显示
- 添加视频缩略图预览功能
- 支持音频文件上传与语音识别

### 中期计划
- 文件管理面板（查看已上传文件，管理生命周期）
- 多语言支持（UI国际化）
- 插件系统框架
- 加入图像生成功能（DALL-E, Midjourney等）
- 加入音频生成功能（TTS, 音乐生成）
- 多模态文件混合分析优化

### 长期计划
- 本地模型支持（Ollama、LM Studio等）
- 协作功能，多用户对话
- 移动端适配

## 📊 技术栈

- **前端框架**：PyQt6
- **AI SDK**：Google GenAI SDK, OpenAI SDK
- **数据库**：SQLite（本地）/ ODBC（远程）
- **多模态**：Gemini File API, Vision API
- **网络**：自动代理配置，gRPC 认证隔离
- **测试**：自动化测试套件

## 📝 更新日志

- **2025-10-16 (v1.3.1)**：🔧 **Function Calling 增强：高级搜索参数**
  - 🆕 新增 `search_recency_filter`：时效性过滤（day/week/month/year）
  - 🆕 新增 `site_filter`：网站限定（支持最多20个权威站点）
  - 📝 更新 `baidu_searcher.py` 工具 Schema，LLM 可自动使用高级参数
  - 🎯 显著提升天气、新闻等实时信息查询的准确性
  - 📚 新增完整文档：`BAIDU_SEARCHER_ADVANCED_PARAMS.md`
  - 🧪 新增4个测试用例验证高级参数功能
- **2025-10-16 (v1.3.0)**：🤖 **重大更新：Function Calling 框架**
  - ✅ 新增 `baidu_searcher.py`（270行）：百度千帆搜索工具封装
  - ✅ 新增 `tool_executor.py`（280行）：通用工具执行器和注册管理
  - ✅ 升级 `api_client.py`：完整实现 DeepSeek、Gemini 的 Function Calling 支持
  - ✅ 新增 `test_function_calling.py`（260行）：完整测试套件（5个测试场景）
  - 🔄 两步走循环：LLM 决策 → 工具执行 → 上下文注入 → 最终答案
  - 📚 新增 `UPDATE_2025-10-16_function_calling.md`：完整技术文档
  - 🎯 应用场景：实时信息查询、知识增强、智能问答
  - 🔧 可扩展架构：轻松添加天气、计算器等新工具
- **2025-10-16**：🎨 用户体验优化三连击：(1)创作面板去边框+动态单词计数(xx/75)颜色预警；(2)SD生成进度实时反馈（渐变背景+图标+步骤详情）；(3)代码结构重构（model_registry.py统一模型配置，sd_config.py参数持久化）
- **2025-10-15**：🎨 新增 Stable Diffusion 创作控制面板（CFG 支持 0.5 步长、数值框移除上下按钮、滚轮微调精度优化），并修复 SD WebUI 在全局代理下被劫持导致的 502 问题；新增模型自动刷新与切换支持。
- **2025-10-10**：✨ 完全支持视频附件，用户气泡底部有引用文件显示，优化UI交互
- **2025-10-10**：✨ Gemini 视频理解支持，文件类型重构（仅图片/PDF/视频），气泡文件引用显示
- **2025-10-09**：🔧 修复 Gemini 文件上传代理冲突
- **2025-10-08**：🐛 气泡布局修复，文件上传优化
- **2025-10-05**：🔍 高级文本搜索功能
- **2025-09-30**：🎨 气泡自适应布局优化
- **2025-09-28**：🌓 深色模式与主题管理

详见 `LOG/` 目录下的详细更新日志。

## 🤝 贡献指南

请遵循开发准则（见文档顶部），所有改动需要：
1. 记录到日志文件夹 LOG
2. 更新 README 项目结构
3. 完成开发链条：idea → 目的 → 必要性 → 可行性 → 执行
4. 每日存档提交到 GitHub
5. 协调开发时间，确保单人编辑

## 📧 联系方式

- Email: 946163076@QQ.com
- Issues: 欢迎提交问题和建议

## 📄 许可证

本项目仅供学习和个人使用。