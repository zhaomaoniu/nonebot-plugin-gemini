import os
import aiohttp
import google.generativeai as genai

from io import BytesIO
from PIL import Image as PILImage
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.adapters import Message, Event, Bot
from nonebot import require, get_driver, on_command
from nonebot.params import CommandArg, ArgPlainText
from google.generativeai.generative_models import ChatSession

from .config import Config

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
    supported_adapters=None,
)


plugin_config = Config.parse_obj(get_driver().config)


GOOGLE_API_KEY = plugin_config.google_api_key or os.environ.get("GOOGLE_API_KEY", None)


if GOOGLE_API_KEY is None:
    raise ValueError("GOOGLE_API_KEY 未配置, nonebot-plugin-gemini 无法运行")


genai.configure(api_key=GOOGLE_API_KEY)

models = {
    "gemini-pro": genai.GenerativeModel("gemini-pro"),
    "gemini-pro-vision": genai.GenerativeModel("gemini-pro-vision"),
}


async def to_markdown(text: str) -> bytes:
    text = text.replace("•", "  *")
    return await md_to_pic(text, width=800)


async def to_pil_image(image: Image) -> PILImage:
    if image.raw is not None:
        return PILImage.open(
            image.raw.getvalue() if isinstance(image.raw, BytesIO) else image.raw
        )

    try:
        return PILImage.open(image.raw_bytes)
    except ValueError:
        pass

    if image.path is not None:
        return PILImage.open(image.path)

    if image.url is not None:
        async with aiohttp.ClientSession() as session:
            async with session.get(image.url) as resp:
                data = await resp.read()
                return PILImage.open(BytesIO(data))

    raise ValueError("无法获取图片")


chat = on_command("gemini", priority=10, block=True)
conversation = on_command("geminichat", priority=5, block=True)


@chat.handle()
async def _(event: Event, bot: Bot, message: Message = CommandArg()):
    uni_message = await UniMessage.generate(message=message, event=event, bot=bot)

    msg = []
    model = "gemini-pro"

    for seg in uni_message:
        if isinstance(seg, Text):
            msg.append(seg.text)

        elif isinstance(seg, Image):
            model = "gemini-pro-vision"
            msg.append(await to_pil_image(seg))

    if not msg:
        await chat.finish("未获取到有效输入，输入应为文本或图片")

    try:
        resp = await models[model].generate_content_async(msg)
    except Exception as e:
        await chat.finish(f"{type(e).__name__}: {e}")

    try:
        result = resp.text
    except ValueError:
        result = "\n---\n".join(
            [part.text for part in resp.candidates[0].content.parts]
        )

    await chat.finish(
        await UniMessage(Image(raw=await to_markdown(result))).export()
        if len(result) > 500
        else result.strip()
    )


@conversation.handle()
async def start_conversation(
    state: T_State, matcher: Matcher, args: Message = CommandArg()
):
    if args.extract_plain_text() != "":
        matcher.set_arg(key="msg", message=args)

    state["gemini_chat_session"] = models["gemini-pro"].start_chat(history=[])


@conversation.got("msg", prompt="对话开始")
async def got_message(state: T_State, msg: str = ArgPlainText()):
    if msg in ["结束", "结束对话", "结束会话", "stop", "quit"]:
        await conversation.finish("对话结束")

    chat_session: ChatSession = state["gemini_chat_session"]

    try:
        resp = await chat_session.send_message_async(msg)
    except Exception as e:
        await conversation.finish(f"发生意外错误，对话已结束\n{type(e).__name__}: {e}")

    try:
        result = resp.text
    except ValueError:
        result = "\n---\n".join(
            [part.text for part in resp.candidates[0].content.parts]
        )

    await conversation.reject(
        await UniMessage(Image(raw=await to_markdown(result))).export()
        if len(result) > 500
        else result.strip()
    )
