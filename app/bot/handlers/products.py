from math import ceil
import os
import re
import uuid
from decimal import Decimal
from collections import defaultdict
import httpx

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

from sqlalchemy.orm import Session

from app.repositories.user_repo import get_by_tg_id as get_user_by_tg_id
from app.models.user import User
from app.db.session import SessionLocal
from app.repositories.product_repo import list_active_by_category, get_by_id as get_product
from app.bot.keyboards.common import main_menu
from app.models.order import Order
from app.repositories.wallet_repo import get_wallet_usd

# التوكن و API
_API_TOKEN = "ace7f794532f369ba7d8008a1782178cc082c808b82cb57c"
_API_BASE = "https://api.jentel-cash.com/client/api/newOrder"

router = Router()

# تخطيط القوائم
GAME_COLUMNS = 2
GAME_ROWS = 5
PRODUCTS_PER_PAGE = GAME_COLUMNS * GAME_ROWS  # =10

APP_COLUMNS = 3
APP_ROWS = 8
APP_PER_PAGE = APP_COLUMNS * APP_ROWS         # =24

class OrderFlow(StatesGroup):
    waiting_qty = State()
    waiting_player_id = State()

def db_session() -> Session:
    return SessionLocal()

def _unit_price_usd(p) -> Decimal:
    c = Decimal(str(p.cost_per_unit_usd or 0))
    pr = Decimal(str(p.profit or 0))
    return c + pr

def extract_base_name(name: str) -> str:
    name = name.lower().strip()
    remove_words = {"coins","coin","usd","diamonds","diamond","gems","gem","package","pack"}
    name = re.sub(r"[\d\+\-]+", " ", name)
    parts = [w for w in name.split() if w not in remove_words]
    return " ".join(parts).strip()

def group_products(products):
    groups = defaultdict(list)
    for p in products:
        base_name = extract_base_name(p.name)
        groups[base_name].append(p)
    return groups

def _page_kb(items, category: str, page: int, total: int, per_row: int) -> InlineKeyboardMarkup:
    total_pages = max(1, ceil(total / (APP_PER_PAGE if category == "chat" else PRODUCTS_PER_PAGE)))
    rows, row = [], []
    for i, base_name in enumerate(items, start=1):
        row.append(InlineKeyboardButton(text=base_name.upper()[:30],
                                        callback_data=f"group:{category}:{base_name}"))
        if i % per_row == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅ السابق", callback_data=f"prodpage:{category}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"صفحة {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="التالي ➡", callback_data=f"prodpage:{category}:{page+1}"))
    rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def _product_back_btn(pid: int, category: str, base_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ العودة", callback_data=f"group:{category}:{base_name}")]
        ]
    )

async def _send_page(message_or_cb, category: str, page: int, edit: bool = False):
    db = db_session()
    try:
        all_prods = list_active_by_category(db, category)
        if not all_prods:
            if edit:
                return await message_or_cb.message.edit_text("لا توجد عناصر متاحة حالياً.", reply_markup=main_menu())
            return await message_or_cb.answer("لا توجد عناصر متاحة حالياً.", reply_markup=main_menu())

        grouped = group_products(all_prods)
        all_groups = sorted(grouped.keys())

        if category == "chat":
            per_page = APP_PER_PAGE
            per_row = APP_COLUMNS
        else:
            per_page = PRODUCTS_PER_PAGE
            per_row = GAME_COLUMNS

        total = len(all_groups)
        total_pages = max(1, ceil(total / per_page))
        page = max(1, min(page, total_pages))

        start = (page - 1) * per_page
        end = start + per_page
        page_groups = all_groups[start:end]

        kb = _page_kb(page_groups, category, page, total, per_row)
        text = "اختر لعبة:" if category == "game" else "اختر تطبيق:"

        if edit:
            return await message_or_cb.message.edit_text(text, reply_markup=kb)
        else:
            return await message_or_cb.answer(text, reply_markup=kb)
    finally:
        db.close()

@router.message(F.text == "🎮 شحن لعبة")
async def choose_game(message: Message):
    await _send_page(message, "game", 1, edit=False)

@router.message(F.text == "💬 شحن تطبيق")
async def choose_app(message: Message):
    await _send_page(message, "chat", 1, edit=False)

@router.callback_query(F.data.startswith("prodpage:"))
async def products_pagination(cb: CallbackQuery):
    _, category, page = cb.data.split(":")
    await _send_page(cb, category, int(page), edit=True)
    await cb.answer()

@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer("")

@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery):
    await cb.message.edit_text("اختر من القائمة:", reply_markup=main_menu())
    await cb.answer()

@router.callback_query(F.data.startswith("group:"))
async def group_selected(cb: CallbackQuery):
    _, category, base_name = cb.data.split(":", 2)
    db = db_session()
    try:
        all_prods = list_active_by_category(db, category)
        grouped = group_products(all_prods)
        products_in_group = grouped.get(base_name, [])
        if not products_in_group:
            await cb.answer("لا توجد منتجات", show_alert=True)
            return

        per_row = APP_COLUMNS if category == "chat" else GAME_COLUMNS

        rows, row = [], []
        for i, p in enumerate(products_in_group, start=1):
            row.append(InlineKeyboardButton(
                text=p.name.upper()[:30],
                callback_data=f"prod:{p.id}:{category}:{base_name}"
            ))
            if i % per_row == 0:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton(
            text="⬅ العودة للقوائم",
            callback_data=f"back_groups:{category}"
        )])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

        if cb.message.photo:
            await cb.message.delete()
            await cb.message.answer(f"اختر منتج من {base_name}:", reply_markup=kb)
        else:
            try:
                await cb.message.edit_text(f"اختر منتج من {base_name}:", reply_markup=kb)
            except:
                await cb.message.answer(f"اختر منتج من {base_name}:", reply_markup=kb)
    finally:
        db.close()

@router.callback_query(F.data.startswith("back_groups:"))
async def back_groups(cb: CallbackQuery):
    _, category = cb.data.split(":")
    await _send_page(cb, category, 1, edit=True)
    await cb.answer()

async def _show_product_details(cb: CallbackQuery, p, category: str, base_name: str):
    kind = (p.unit_label or "").lower()
    back_btn = _product_back_btn(p.id, category, base_name)
    price = _unit_price_usd(p)

    if kind == "amount":
        text = (
            f"المنتج: <b>{p.name.upper()}</b>\n"
            f"السعر للوحدة: <b>{price}</b> USD\n"
            f"أدخل الكمية (بين {p.min_qty or 1} و {p.max_qty or '∞'}):"
        )
    elif kind in ("package", "pacage"):
        text = (
            f"المنتج: <b>{p.name.upper()}</b>\n"
            f"النوع: باقة\n"
            f"السعر: <b>{price}</b> USD\n"
            f"الرجاء إدخال <b>ID</b> الخاص بالحساب المراد شحنه:"
        )
    else:
        text = f"المنتج: <b>{p.name.upper()}</b>\nنوع غير معروف: {p.unit_label}"

    pkg_fname = re.sub(r"\s+", "", base_name).lower() + ".jpg"
    img_rel = f"static/uploads/products/{pkg_fname}"
    img_abs = os.path.abspath(img_rel)

    if os.path.exists(img_abs):
        await cb.message.answer_photo(
            photo=FSInputFile(img_abs),
            caption=text,
            reply_markup=back_btn
        )
        try:
            await cb.message.delete()
        except:
            pass
    else:
        try:
            await cb.message.edit_text(text, reply_markup=back_btn)
        except:
            await cb.message.answer(text, reply_markup=back_btn)

@router.callback_query(F.data.startswith("prod:"))
async def product_selected(cb: CallbackQuery, state: FSMContext):
    db = db_session()
    try:
        pid, category, base_name = cb.data.split(":")[1:]
        pid = int(pid)
        p = get_product(db, pid)
        if not p or not p.is_active:
            await cb.answer("غير متاح", show_alert=True); return

        provider_product_id = str(p.num) if getattr(p, "num", None) else None
        if not provider_product_id:
            await cb.answer("هذا المنتج بلا معرف مزوّد (num).", show_alert=True)
            return

        await state.update_data(
            product_id=p.id,
            provider_product_id=provider_product_id,
            product_name=p.name,
            unit_price_usd=float(_unit_price_usd(p)),
            category=category,
            base_name=base_name,
            min_qty=p.min_qty or 1,
            max_qty=p.max_qty,
            unit_label=(p.unit_label or "").lower()
        )

        kind = (p.unit_label or "").lower()
        if kind == "amount":
            await state.set_state(OrderFlow.waiting_qty)
        elif kind in ("package", "pacage"):
            await state.set_state(OrderFlow.waiting_player_id)
        await _show_product_details(cb, p, category, base_name)
        await cb.answer()
    finally:
        db.close()

@router.message(OrderFlow.waiting_qty)
async def handle_qty(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        qty = int(message.text.strip())
    except:
        await message.answer("أدخل رقم صحيح.")
        return

    if qty < int(data.get("min_qty", 1)):
        await message.answer(f"الحد الأدنى {data.get('min_qty')}.")
        return
    if data.get("max_qty") and qty > int(data["max_qty"]):
        await message.answer(f"الحد الأقصى {data['max_qty']}.")
        return

    await state.update_data(qty=qty)

    unit_price = Decimal(str(data.get("unit_price_usd", 0)))
    total_price = unit_price * qty

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="⬅ العودة",
            callback_data=f"prod:{data['product_id']}:{data['category']}:{data['base_name']}")]]
    )

    await state.set_state(OrderFlow.waiting_player_id)
    await message.answer(
        f"السعر الكلي: <b>{total_price:.3f} USD</b>\n\n"
        "أدخل ID الحساب:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.message(OrderFlow.waiting_player_id)
async def handle_player_id(message: Message, state: FSMContext):
    player_id = message.text.strip()
    if not player_id:
        await message.answer("ID غير صالح.")
        return

    data = await state.get_data()
    final_qty = 1 if data.get("unit_label") in ("package", "pacage") else int(data.get("qty", 1))
    unit_price = Decimal(str(data.get("unit_price_usd", 0)))
    total_price = unit_price * final_qty

    await state.update_data(player_id=player_id, final_qty=final_qty, total_price=str(total_price))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأكيد", callback_data="confirm_order"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_order")
            ],
            [
                InlineKeyboardButton(
                    text="⬅ تعديل",
                    callback_data=f"prod:{data['product_id']}:{data['category']}:{data['base_name']}"
                )
            ]
        ]
    )

    await message.answer(
        f"🔎 تفاصيل الطلب:\n\n"
        f"المنتج: <b>{data['product_name']}</b>\n"
        f"الكمية: {final_qty}\n"
        f"السعر الكلي: <b>{total_price:.3f} USD</b>\n"
        f"Player ID: <code>{player_id}</code>\n\n"
        "هل ترغب بمتابعة الطلب؟",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel_order")
async def cancel_order(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text("❌ تم إلغاء العملية.", reply_markup=main_menu())
    except:
        await cb.message.answer("❌ تم إلغاء العملية.", reply_markup=main_menu())
    await cb.answer()

@router.callback_query(F.data == "confirm_order")
async def confirm_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_uuid = str(uuid.uuid4())

    db = db_session()
    try:
        # المستخدم والمحفظة
        tg_id = cb.from_user.id
        user = get_user_by_tg_id(db, tg_id)
        if not user:
            user = User(tg_id=tg_id, name=cb.from_user.full_name or "")
            db.add(user)
            db.commit()
            db.refresh(user)

        wallet = get_wallet_usd(db, user.id)
        if not wallet:
            await cb.message.answer("❌ لا يوجد لديك محفظة USD.", reply_markup=main_menu())
            await state.clear()
            await cb.answer()
            return

        final_qty = int(data.get("final_qty", 1))
        total_price = Decimal(str(data.get("total_price", "0")))
        provider_product_id = data.get("provider_product_id")
        player_id = data.get("player_id")

        # تحقق الرصيد
        if wallet.balance < total_price:
            await cb.message.answer(
                f"❌ رصيدك غير كافٍ لهذه العملية.\n"
                f"رصيدك الحالي: {wallet.balance} USD\n"
                f"السعر المطلوب: {total_price} USD\n"
                f"الرجاء شحن المحفظة",
                reply_markup=main_menu()
            )
            await state.clear()
            await cb.answer()
            return

        # إنشاء سجل الطلب محلياً
        order = Order(
            user_id=user.id,
            product_id=data["product_id"],
            provider_product_id=provider_product_id,
            order_uuid=order_uuid,
            product_name=data["product_name"],
            qty=final_qty,
            target=player_id,
            unit_price_usd=data.get("unit_price_usd", 0),
            total_price_usd=total_price,
            status="created"
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # استدعاء المزوّد
        url = f"{_API_BASE}/{provider_product_id}/params"
        params = {"qty": str(final_qty), "playerId": player_id, "order_uuid": order_uuid}
        headers = {"api-token": _API_TOKEN, "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=headers)

        try:
            payload = r.json()
        except:
            payload = {"raw": r.text}

        if 200 <= r.status_code < 300 and payload.get("status") == "OK":
            data_resp = payload.get("data", {})
            order.status = "sent"
            order.provider_order_id = data_resp.get("order_id")
            order.provider_status = data_resp.get("status")
            order.provider_price_usd = data_resp.get("price")
            order.provider_payload = r.text

            # خصم الرصيد
            try:
                wallet.balance = (wallet.balance - total_price)
                db.add(wallet)
            except Exception:
                order.status = "failed"
                order.error_msg = "فشل خصم الرصيد"
                db.commit()
                await cb.message.answer("❌ حدث خطأ أثناء خصم الرصيد. لم يتم تنفيذ العملية.", reply_markup=main_menu())
                await state.clear()
                await cb.answer()
                return

            db.commit()

            status_map = {"wait": "قيد المعالجة", "accept": "تم القبول", "reject": "مرفوض"}
            status_txt = status_map.get(str(order.provider_status).lower(), order.provider_status)

            try:
                await cb.message.edit_text(
                    f"✅ تم إنشاء الطلب بنجاح\n"
                    f"رقم الطلب: {order.provider_order_id}\n"
                    f"الحالة: {status_txt}\n"
                    f"السعر: {order.total_price_usd} USD\n"
                    f"الرصيد المتبقي: {wallet.balance} USD",
                    reply_markup=main_menu()
                )
            except:
                await cb.message.answer(
                    f"✅ تم إنشاء الطلب بنجاح\n"
                    f"رقم الطلب: {order.provider_order_id}\n"
                    f"الحالة: {status_txt}\n"
                    f"السعر: {order.total_price_usd} USD\n"
                    f"الرصيد المتبقي: {wallet.balance} USD",
                    reply_markup=main_menu()
                )

            await state.clear()
            await cb.answer()
            return

        # فشل من المزوّد
        order.status = "failed"
        order.error_msg = f"رد غير ناجح: {r.status_code}"
        db.commit()
        try:
            await cb.message.edit_text("❌ فشل إنشاء الطلب لدى المزوّد.", reply_markup=main_menu())
        except:
            await cb.message.answer("❌ فشل إنشاء الطلب لدى المزوّد.", reply_markup=main_menu())

    except httpx.RequestError as e:
        try:
            order.status = "failed"
            order.error_msg = f"اتصال فشل: {e}"
            db.commit()
        except:
            pass
        await cb.message.answer(f"❌ خطأ اتصال: {e}", reply_markup=main_menu())
    finally:
        db.close()
        await state.clear()
        await cb.answer()

@router.message(F.text == "📦 سجل شحن التطبيقات")
async def check_orders(message: Message):
    db = db_session()
    try:
        from app.repositories.user_repo import get_by_tg_id
        user = get_by_tg_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ لا يوجد لديك حساب.")
            return

        # جلب آخر 5 طلبات للمستخدم
        last_orders = db.query(Order).filter(
            Order.user_id == user.id,
            Order.provider_order_id.isnot(None)
        ).order_by(Order.created_at.desc()).limit(5).all()

        if not last_orders:
            await message.answer("📭 لا يوجد طلبات سابقة.")
            return

        order_ids_str = ",".join([o.provider_order_id for o in last_orders])

        # طلب الحالات من API
        url = "https://api.jentel-cash.com/client/api/check"
        headers = {"api-token": _API_TOKEN}
        params = {"orders": order_ids_str}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers, params=params)

        try:
            payload = r.json()
        except Exception:
            await message.answer("❌ فشل قراءة الرد من المزود.")
            return

        # تحديث الحالات
        status_map = {
            "wait": ("⏳", "قيد المعالجة"),
            "accept": ("✅", "تم القبول"),
            "reject": ("❌", "مرفوض")
        }

        if payload.get("status") == "OK":
            for od in payload.get("data", []):
                oid = od.get("order_id")
                new_status = od.get("status")
                order_row = next((o for o in last_orders if o.provider_order_id == oid), None)
                if order_row:
                    order_row.provider_status = new_status
                    if str(new_status).lower() == "accept":
                        order_row.status = "completed"
                    elif str(new_status).lower() == "reject":
                        order_row.status = "failed"
                    db.add(order_row)
            db.commit()

        # إعادة الجلب بعد التحديث
        last_orders = db.query(Order).filter(
            Order.user_id == user.id,
            Order.provider_order_id.isnot(None)
        ).order_by(Order.created_at.desc()).limit(5).all()

        # تجهيز الرسالة
        text = "📋 **آخر 5 طلبات**\n\n"
        for i, o in enumerate(last_orders):
            emoji, status_text = status_map.get(
                str(o.provider_status).lower(),
                ("ℹ️", str(o.provider_status))
            )
            text += (
                f"{emoji} **{o.product_name}**\n"
                f"رقم الطلب: `{o.provider_order_id}`\n"
                f"الحالة: {status_text}\n"
                f"السعر: {o.total_price_usd} USD\n"
                f"Player ID: `{o.target}`\n"
                f"التاريخ: {o.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
            if i < len(last_orders) - 1:
                text += "──────────\n"

        await message.answer(text, parse_mode="Markdown")

    except httpx.RequestError as e:
        await message.answer(f"⚠️ خطأ اتصال: {e}")
    finally:
        db.close()
