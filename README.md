# Agent 项目

这是一个包含开发工具的个人助手项目，使用Deepseek-V3模型，后续会接入更多其他模型

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

## 项目结构

- `SoftWare/Script/` - 所有脚本文件
  - `dev_notebook.py` - 开发记事本工具
  api_client
  - `main.py` - 主程序
  - `chat_ui.py` - UI_聊天界面
  -`api_client` -API调用
  -`bubble_copy_handler` -对话气泡设置
  -`chat_area` -UI_聊天区域
  -`database_manager` -数据库_配置DSN管理
  -`dialogs` -UI_软件弹窗类
  -`file_manager` -数据库_不配置DSN时本地对话管理
  -`input_bar` -UI_输入栏
  -`sidebar` -UI_对话任务管理栏
  -`storage_config` -数据库_使用/不使用DSN 逻辑切换

- `SoftWare/Image` - 所有软件内所需资源
 - `Backgroud` - UI背景图片
 - `loading` - Agent回答加载中GIF文件

- `SoftWare/Icon` - 软件封装图标

## 使用方法

1. 安装依赖：`pip install -r requirements.txt`
2. 运行main.py：`python SoftWare/Script/main.py`
3. 运行Agent开发指令模板：`python SoftWare/Script/dev_notebook`

## 功能特性

- 联网即可使用个人助手问答 
- 本地保存对话记录不泄密
- 预设提示词提高问答效率
- 任务管理栏滚动播放任务名称
- UI界面可缩放至任意大小

## 相较前版本改动：

- 更正且丰富Readme文件描述

## 未来开发计划：
- 
- 
- 