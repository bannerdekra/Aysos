## 开发者如何使用?

### 1. 调整您的环境路径
目的：确保 Python 能找到所需的库文件，在开发过程中确保您使用终端不报错

- 步骤1：修改setting.json文件中`python`的路径
  - 打开 `Agent/.vscode/` 目录下的 `setting.json` 文件
  - 找到 `"python.defaultInterpreterPath":`，修改为您的python路径，例如："E:\\Anaconda\\envs\\chatbot\\python.exe",

- 步骤2：修改setting.json文件中`condaPath`的路径
  - 打开 `Agent/.vscode/` 目录下的 `setting.json` 文件
  - 找到 `"python.condaPath":`，修改为您的conda路径，例如："E:\\Anaconda\\Scripts\\conda.exe",

完成以上两步相信您已经可以在终端中成功运行项目python脚本了，如果提示您缺乏某种环境，使用PIP指令下载即可！

