import os
import aiohttp

from io import BytesIO
from typing import Union
from pathlib import Path
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters import Message, Event, Bot
from nonebot import require, get_driver, on_command
from nonebot.params import CommandArg, ArgPlainText
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import Config
from .gemini import Gemini, GeminiChatSession

require("nonebot_plugin_alconna")
require("nonebot_plugin_htmlrender")

from nonebot_plugin_alconna import UniMessage, Text, Image
from nonebot_plugin_htmlrender import md_to_pic


__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-gemini",
    description="Gemini AI 对话",
    usage="gemini [文本/图片] -Gemini 生成回复\ngeminichat (可选)[文本] -开始 Gemini 对话\n结束对话 -结束 Gemini 对话",
    type="application",
    homepage="https://github.com/zhaomaoniu/nonebot-plugin-gemini",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)


plugin_config = Config.parse_obj(get_driver().config)


GOOGLE_API_KEY = plugin_config.google_api_key or os.environ.get("GOOGLE_API_KEY", None)


if GOOGLE_API_KEY is None:
    raise ValueError("GOOGLE_API_KEY 未配置, nonebot-plugin-gemini 无法运行")


gemini = Gemini(GOOGLE_API_KEY, plugin_config.proxy)


async def to_markdown(text: str) -> bytes:
    text = text.replace("•", "  *")
    return await md_to_pic(text, width=800)


async def to_image_data(image: Image) -> Union[BytesIO, bytes]:
    if image.raw is not None:
        return image.raw

    if image.path is not None:
        return Path(image.path).read_bytes()

    if image.url is not None:
        async with aiohttp.ClientSession() as session:
            async with session.get(image.url) as resp:
                return await resp.read()

    raise ValueError("无法获取图片数据")


chat = on_command("gemini", priority=10, block=True)
conversation = on_command("geminichat", priority=5, block=True)


@chat.handle()
async def _(event: Event, bot: Bot, message: Message = CommandArg()):
    uni_message = await UniMessage.generate(message=message, event=event, bot=bot)

    msg = []

    for seg in uni_message:
        if isinstance(seg, Text) and seg.text.strip() != "":
            # 防止空文本导致 Gemini 生成莫名其妙的回复
            msg.append(seg.text)

        elif isinstance(seg, Image):
            msg.append(await to_image_data(seg))

    if not msg:
        await chat.finish("未获取到有效输入，输入应为文本或图片")

    try:
        resp = await gemini.generate(msg)
    except Exception as e:
        await chat.finish(f"{type(e).__name__}: {e}")

    try:
        result = resp["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError:
        result = "未获取到有效回复"

    await chat.finish(
        await UniMessage(Image(raw=await to_markdown(result))).export()
        if len(result) > plugin_config.image_render_length
        else result.strip()
    )


@conversation.handle()
async def start_conversation(
    state: T_State, matcher: Matcher, args: Message = CommandArg()
):
    if args.extract_plain_text() != "":
        matcher.set_arg(key="msg", message=args)

    state["gemini_chat_session"] = GeminiChatSession(GOOGLE_API_KEY, plugin_config.proxy)


@conversation.got("msg", prompt="对话开始")
async def got_message(state: T_State, msg: str = ArgPlainText()):
    if msg in ["结束", "结束对话", "结束会话", "stop", "quit"]:
        await conversation.finish("对话结束")

    chat_session: GeminiChatSession = state["gemini_chat_session"]

    try:
        resp = await chat_session.send_message(msg)
    except Exception as e:
        await conversation.finish(f"发生意外错误，对话已结束\n{type(e).__name__}: {e}")

    try:
        result = resp["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError:
        result = "未获取到有效回复"

    await conversation.reject(
        await UniMessage(Image(raw=await to_markdown(result))).export()
        if len(result) > plugin_config.image_render_length
        else result.strip()
    )
