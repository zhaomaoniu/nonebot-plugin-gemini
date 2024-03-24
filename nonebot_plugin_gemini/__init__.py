import os
import fleep
import aiohttp
import nonebot
from io import BytesIO
from typing import Union
from pathlib import Path
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
import google.generativeai as genai
from nonebot import require, on_command
import google.ai.generativelanguage as glm
from nonebot.adapters import Message, Event, Bot
from nonebot.params import CommandArg, ArgPlainText, EventMessage
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import Config
from .search_engines import GoogleSearch

require("nonebot_plugin_alconna")
require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender import md_to_pic
from nonebot_plugin_alconna import UniMessage, Text, Image, Reply


__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-gemini",
    description="Gemini AI 对话",
    usage="gemini [文本/图片] -Gemini 生成回复\ngeminichat (可选)[文本] -开始 Gemini 对话\n结束对话 -结束 Gemini 对话",
    type="application",
    homepage="https://github.com/zhaomaoniu/nonebot-plugin-gemini",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)


if hasattr(nonebot, "get_plugin_config"):
    plugin_config = nonebot.get_plugin_config(Config)
else:
    from nonebot import get_driver

    plugin_config = Config.parse_obj(get_driver().config)


GOOGLE_API_KEY = plugin_config.google_api_key or os.environ.get("GOOGLE_API_KEY", None)


if GOOGLE_API_KEY is None:
    raise ValueError("GOOGLE_API_KEY 未配置, nonebot-plugin-gemini 无法运行")


google_search = (
    GoogleSearch(
        plugin_config.google_custom_search_key,
        plugin_config.google_custom_search_cx,
        plugin_config.google_custom_search_num,
        plugin_config.proxy,
    )
    if plugin_config.enable_search
    else None
)
search = glm.Tool(
    function_declarations=[
        glm.FunctionDeclaration(
            name="internet_search",
            description="Search the internet for information",
            parameters=glm.Schema(
                type=glm.Type.OBJECT,
                properties={
                    "topic": glm.Schema(type=glm.Type.STRING),
                },
                required=["topic"],
            ),
        )
    ]
)


genai.configure(api_key=GOOGLE_API_KEY)

# 配置代理
if plugin_config.proxy is not None:
    os.environ["http_proxy"] = plugin_config.proxy
    os.environ["https_proxy"] = plugin_config.proxy


async def get_uni_reply(reply: Reply, event: Event, bot: Bot) -> UniMessage:
    if reply.msg is None:
        raise ValueError("回复为空")

    if isinstance(reply.msg, str):
        return UniMessage([Text(reply.msg)])
    elif isinstance(reply.msg, Message):
        return await UniMessage.generate(message=reply.msg, event=event, bot=bot)


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
                if resp.status != 200:
                    raise ValueError(f"无法获取图片数据: {resp.status}")
                return await resp.read()

    raise ValueError("无法获取图片数据")


async def send_message_to_gemini(
    msg: genai.types.ContentType,
    model_name: str,
    chat_session: genai.ChatSession = None,
):
    try:
        model = genai.GenerativeModel(
            model_name,
            tools=(
                search
                if model_name == "gemini-pro" and plugin_config.enable_search
                # 只有 Gemini Pro 支持 Function Call
                else None
            ),
        )

        chat_session = (
            (
                model.start_chat(
                    enable_automatic_function_calling=plugin_config.enable_search
                )
            )
            if chat_session is None
            else chat_session
        )
        resp = await chat_session.send_message_async(msg)
        # 检查是否需要调用搜索功能
        if plugin_config.enable_search and model_name == "gemini-pro":
            try:
                fc = resp.candidates[0].content.parts[0].function_call

                if fc.name != "internet_search":
                    raise ValueError("未检测到搜索功能调用")

                logger.info(f"搜索功能调用: {fc.args['topic']}")

                results = await google_search.get_results([fc.args["topic"]])
                result = "\n\n".join(
                    f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['text']}"
                    for r in results
                )
                response = await chat_session.send_message_async(
                    glm.Content(
                        parts=[
                            glm.Part(
                                function_response=glm.FunctionResponse(
                                    name="internet_search", response={"result": result}
                                )
                            )
                        ]
                    )
                )
            except (ValueError, KeyError):
                response = resp
        else:
            response = resp
        try:
            result = response.candidates[0].content.parts[0].text
        except KeyError:
            result = "未获取到有效回复"
    except Exception as e:
        result = f"{type(e).__name__}: {e}"

    return result


chat = on_command("gemini", priority=10, block=True)
conversation = on_command("geminichat", priority=5, block=True)


@chat.handle()
async def _(
    event: Event,
    bot: Bot,
    message: Message = CommandArg(),
    raw_message: Message = EventMessage(),
):
    uni_message = await UniMessage.generate(message=message, event=event, bot=bot)
    uni_message_raw = await UniMessage.generate(
        message=raw_message, event=event, bot=bot
    )

    msg = []
    reply = uni_message_raw[Reply, 0] if Reply in uni_message_raw else None
    model_name = "gemini-pro"

    if reply is not None and reply.msg is not None:
        uni_message = (await get_uni_reply(reply, event, bot)).include(
            Image, Text
        ) + uni_message

    for seg in uni_message:
        if isinstance(seg, Text) and seg.text.strip() != "":
            # 防止空文本导致 Gemini 生成莫名其妙的回复
            msg.append(glm.Part(text=seg.text))

        elif isinstance(seg, Image):
            model_name = "gemini-pro-vision"
            image_data = await to_image_data(seg)
            info = fleep.get(image_data[:128])

            try:
                mine_type = info.mime[0]
            except KeyError:
                raise ValueError("无法识别图片类型")

            msg.append(
                glm.Part(inline_data=glm.Blob(mime_type=mine_type, data=image_data))
            )

        else:
            msg.append(str(seg))

    if not msg:
        await chat.finish("未获取到有效输入，输入应为文本或图片")

    result = await send_message_to_gemini(msg, model_name)

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

    state["gemini_chat_session"] = genai.GenerativeModel(
        "gemini-pro", tools=search if plugin_config.enable_search else None
    ).start_chat(enable_automatic_function_calling=plugin_config.enable_search)


@conversation.got("msg", prompt="对话开始")
async def got_message(state: T_State, msg: str = ArgPlainText()):
    if msg in ["结束", "结束对话", "结束会话", "stop", "quit"]:
        await conversation.finish("对话结束")

    chat_session: genai.ChatSession = state["gemini_chat_session"]

    try:
        result = await send_message_to_gemini(
            msg, "gemini-pro", chat_session=chat_session
        )
    except Exception as e:
        await conversation.finish(f"发生意外错误，对话已结束\n{type(e).__name__}: {e}")

    await conversation.reject(
        await UniMessage(Image(raw=await to_markdown(result))).export()
        if len(result) > plugin_config.image_render_length
        else result.strip()
    )
