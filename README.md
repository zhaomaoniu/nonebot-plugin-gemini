# Nonebot Plugin Gemini
Google Gemini AI 对话插件

## 功能
| 命令 | 用途 | 示例 |
| --- | --- | --- |
| gemini <文本/图像> | 单次调用 Gemini 并获取回复 | gemini 编写一个NoneBot2的echo插件 |
| geminichat [可选]<文本> | 开启一轮与 Gemini 的对话 | geminichat |
| 结束对话 | 结束本轮对话 | 结束对话 |

> 如果你配置了命令头，请在使用命令时将命令头加上

## 安装方法
<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-gemini

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-gemini
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-gemini
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-gemini
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-gemini
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_gemini"]

</details>


## 配置
在 [Google AI Studio](https://makersuite.google.com/app/apikey) 获取 `GOOGLE_API_KEY` 后，在 .env 文件 或 环境变量 中添加 `GOOGLE_API_KEY`

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| GOOGLE_API_KEY | 无 | Google AI Studio 的 API Key |
| PROXY | 无 | 可选。代理地址，格式为 `http://ip:port` 或 `socks5://ip:port` |
| IMAGE_RENDER_LENGTH | 500 | 可选。超过这个数值的回复将会以 Markdown 渲染为图片 |
