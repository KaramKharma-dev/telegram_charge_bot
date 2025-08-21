from decimal import Decimal, InvalidOperation
from typing import Callable, Awaitable, Any

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.bot.keyboards.common import main_menu
from app.bot.states.topup import TopupFlow

from app.repositories.user_repo import get_by_tg_id
from app.repositories.wallet_repo import get_wallet_usd
from app.repositories.topup_method_repo import list_active, get_by_id
from app.repositories.exchange_repo import get_rate
from app.repositories.wallet_txn_repo import (
    create_pending_topup, list_user_topups, DuplicateOperationRefError, approve_topup
)
from app.repositories.incoming_sms_repo import claim_matching_sms

from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.config import settings

router = Router()

# ---------- DB ----------
def db_session() -> Session:
    return SessionLocal()

# ---------- Middleware لمسح الحالة عند أي تنقّل ----------
NAV_TEXTS = {
    "🎮 شحن لعبة",
    "💬 شحن تطبيق",
    "➕ تعبئة رصيد",
    "💳 الرصيد",
    "🧾 سجل تعبئة المحفظة",
    "/menu",
}
NAV_CB_PREFIXES = ("prodpage:", "group:", "prod:", "back_groups:", "back_main", "topup:")


class StateResetOnNav(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if state:
            if isinstance(event, Message) and (event.text or "") in NAV_TEXTS:
                await state.clear()
            elif isinstance(event, CallbackQuery):
                cd = (event.data or "")
                if cd.startswith(NAV_CB_PREFIXES):
                    await state.clear()
        return await handler(event, data)

router.message.outer_middleware(StateResetOnNav())
router.callback_query.outer_middleware(StateResetOnNav())

# ---------- أوامر عامة ----------
@router.message(F.text == "/menu")
async def menu_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(" من :", reply_markup=main_menu())

@router.message(F.text == "💳 الرصيد")
async def show_balance(message: Message, state: FSMContext):
    await state.clear()
    db = db_session()
    try:
        u = get_by_tg_id(db, message.from_user.id)
        if not u:
            await message.answer("📝 اكتب /start أولاً لإنشاء حسابك.")
            return

        w = get_wallet_usd(db, u.id)
        if not w:
            await message.answer("⚠️ لا توجد محفظة USD مرتبطة بحسابك.")
            return

        await message.answer(
            f"💼 <b>محفظتك</b>\n"
            f"💲 الرصيد الحالي: <b>{w.balance:.2f}</b> {w.currency}",
            parse_mode="HTML",
        )
    finally:
        db.close()

# ---------- تدفّق الشحن ----------
@router.message(F.text == "➕ تعبئة رصيد")
async def topup_entry(message: Message, state: FSMContext):
    await state.clear()
    db = db_session()
    try:
        methods = list_active(db)
        if not methods:
            await message.answer("حالياً لا توجد طرق شحن متاحة.", reply_markup=main_menu())
            return

        rows = [[InlineKeyboardButton(text=m.name, callback_data=f"topup:{m.id}")] for m in methods]
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        await message.answer("اختر طريقة الشحن:", reply_markup=kb)
    finally:
        db.close()

@router.message(F.text == "🧾 سجل تعبئة المحفظة")
async def orders_entry(message: Message, state: FSMContext):
    await state.clear()
    db = db_session()
    try:
        u = get_by_tg_id(db, message.from_user.id)
        if not u:
            await message.answer("اكتب /start أولاً.")
            return

        txns = list_user_topups(db, u.id, limit=5)
        if not txns:
            await message.answer("لا توجد طلبات شحن.", reply_markup=main_menu())
            return

        status_map = {
            "approved": "✅ مقبول",
            "pending":  "🟡 قيد المراجعة",
            "rejected": "🔴 مرفوض",
        }

        parts = []
        sep = "\n" + ("─" * 27) + "\n"
        for t in txns:
            parts.append(
                f"📌 <b>طلب #{t.id}</b>\n"
                f"💰 المبلغ: <b>{t.amount_usd} USD</b>\n"
                f"📅 التاريخ: {t.created_at:%Y-%m-%d %H:%M}\n"
                f"📍 الحالة: <b>{status_map.get(t.status, t.status)}</b>\n"
                f"🔗 المرجع: <code>{t.operation_ref_or_txid or '-'}</code>"
            )

        text = sep.join(parts)
        await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
    finally:
        db.close()

@router.callback_query(F.data.startswith("topup:"))
async def choose_topup_method(callback: CallbackQuery, state: FSMContext):
    db = db_session()
    try:
        method_id = int(callback.data.split(":")[1])
        m = get_by_id(db, method_id)
        if not m or not m.is_active:
            await callback.answer("غير متاح", show_alert=True)
            return

        await state.update_data(topup_method_id=m.id)

        name_lc = (m.name or "").lower()

        is_syriatel = ("syriatel" in name_lc) or ("سيريتيل" in name_lc)
        is_sham = ("sham" in name_lc) or ("شام" in name_lc)

        # حالة Sham Cash → اعرض خيارين: USD أو SYP
        if is_sham:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💵 شحن USD", callback_data="sham:usd"),
                    InlineKeyboardButton(text="💴 شحن ليرة سورية", callback_data="sham:syp"),
                ],
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")],
            ])
            await callback.message.edit_text("اختر نوع العملة لـ Sham Cash:", reply_markup=kb)
            await callback.answer()
            return

        # Syriatel Cash
        if is_syriatel:
            rate = get_rate(db, "SYP", "USD")
            if not rate:
                await callback.answer("سعر الصرف غير مُعرّف.", show_alert=True)
                return

            await state.set_state(TopupFlow.waiting_syp_amount)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
            ])
            await callback.message.edit_text(
                f"أدخل المبلغ بالليرة السورية (مثال: 150000)\n\n"
                f"علماً أن كل 1$ = {rate:.0f}",
                reply_markup=kb
            )
        else:
            # باقي الطرق الافتراضية → USDT
            await state.set_state(TopupFlow.waiting_usdt_amount)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
            ])
            await callback.message.edit_text("أدخل المبلغ بالدولار (مثال: 12.50):", reply_markup=kb)

        await callback.answer()
    finally:
        db.close()

# --- Sham Cash: اختيار الفرع ---
@router.callback_query(F.data.startswith("sham:"))
async def sham_choice(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[1]  # 'usd' أو 'syp'
    db = db_session()
    try:
        data = await state.get_data()
        m = get_by_id(db, int(data["topup_method_id"])) if data.get("topup_method_id") else None
        if not m:
            await cb.answer("انتهت الجلسة. ابدأ من جديد.", show_alert=True)
            return

        if choice == "syp":
            rate = get_rate(db, "SYP", "USD")
            if not rate:
                await cb.answer("سعر الصرف غير مُعرّف.", show_alert=True)
                return

            await state.set_state(TopupFlow.waiting_syp_amount)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
            ])
            await cb.message.edit_text(
                f"أدخل المبلغ بالليرة السورية (مثال: 150000)\n\n"
                f"علماً أن كل 1$ = {rate:.0f}",
                reply_markup=kb
            )
        else:  # usd
            await state.update_data(is_sham_usd=True)
            await state.set_state(TopupFlow.waiting_usdt_amount)  # نعيد استخدام نفس الحالة
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
            ])
            await cb.message.edit_text("أدخل المبلغ بالدولار USD (مثال: 12.50):", reply_markup=kb)

        await cb.answer()
    finally:
        db.close()

@router.message(TopupFlow.waiting_syp_amount)
async def syp_amount_step(message: Message, state: FSMContext):
    # رجوع للقائمة يلغي التدفق
    if (message.text or "") in NAV_TEXTS:
        await state.clear()
        await message.answer("اختر من القائمة:", reply_markup=main_menu())
        return

    db = db_session()
    try:
        # تحقق المستخدم
        u = get_by_tg_id(db, message.from_user.id)
        if not u:
            await message.answer("اكتب /start أولاً.")
            await state.clear()
            return

        # قراءة مبلغ الليرة
        txt = (message.text or "").replace(",", "").strip()
        try:
            syp = Decimal(txt)
            if syp <= 0:
                raise InvalidOperation()
        except Exception:
            await message.answer("قيمة غير صالحة. أعد الإدخال مثل: 150000")
            return

        # سعر الصرف
        rate = get_rate(db, "SYP", "USD")
        if not rate:
            await message.answer("سعر الصرف غير مُعرّف. تواصل مع الدعم.")
            await state.clear()
            return

        usd = (syp / rate).quantize(Decimal("0.01"))

        # معلومات الطريقة
        data = await state.get_data()
        method = get_by_id(db, int(data["topup_method_id"]))
        details = method.details or {}
        name_lc = (method.name or "").lower()

        # --- إذا شام كاش: نعرض العنوان المحفوظ بالـ details["address"]
        if "sham" in name_lc or "شام" in name_lc:
            dest_text = str(details.get("address") or "—")
        else:
            # الطرق الأخرى (سيريتيل كاش)
            phones = []
            for k, v in details.items():
                if str(k).lower().startswith("phone"):
                    if isinstance(v, str):
                        phones.append(v.strip())
                    elif isinstance(v, list):
                        phones.extend(str(x).strip() for x in v)
            dest_text = "\n".join(f"- {p}" for p in phones) if phones else "—"

        # كيبورد
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 تعديل المبلغ", callback_data="edit_amount"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")
            ]
        ])

        # رسالة التأكيد قبل إدخال رقم العملية
        await message.answer(
            f"القيمة بالليرة: <b>{syp}</b> SYP\n"
            f"ستحصل على : <b>{usd}</b> USD\n"
            f"أرسل المبلغ إلى:\n{dest_text}\n"
            f"ثم أرسل <b>رقم العملية</b> هنا.",
            reply_markup=kb,
            parse_mode="HTML"
        )

        # حفظ وتحويل للخطوة التالية
        await state.update_data(amount_usd=str(usd), submitted_amount_syp=int(syp))
        await state.set_state(TopupFlow.waiting_syriatel_txid)
    finally:
        db.close()

@router.callback_query(F.data == "edit_amount")
async def edit_amount(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TopupFlow.waiting_syp_amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
    ])
    await callback.message.edit_text("أدخل المبلغ بالليرة السورية (مثال: 150000):", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "cancel_flow")
async def cancel_flow(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text("تم إلغاء العملية.")
    except:
        pass
    await cb.message.answer("اختر من القائمة:", reply_markup=main_menu())
    await cb.answer()

@router.message(TopupFlow.waiting_syriatel_txid)
async def syt_txid_step(message: Message, state: FSMContext):
    db = db_session()
    try:
        u = get_by_tg_id(db, message.from_user.id)
        if not u:
            await message.answer(" اكتب /start أولاً.")
            await state.clear(); return

        w = get_wallet_usd(db, u.id)
        if not w:
            await message.answer("لا توجد محفظة USD.")
            await state.clear(); return

        data = await state.get_data()
        method_id = int(data["topup_method_id"])
        amount_usd = Decimal(data["amount_usd"])
        txid = message.text.strip()

        # إنشاء معاملة pending
        try:
            tx = create_pending_topup(
                db,
                wallet_id=w.id,
                topup_method_id=method_id,
                amount_usd=amount_usd,
                op_ref=txid,
                note="syriatelcash",
            )
        except DuplicateOperationRefError:
            await message.answer("⚠️ رقم العملية مستخدم من قبل. جرّب غيره.")
            return

        # تحقق تلقائي
        syp_submitted = None
        try:
            syp_submitted = int(str(data.get("submitted_amount_syp")))
        except:
            pass

        matched = claim_matching_sms(
            db,
            op_ref=txid,
            amount_syp=syp_submitted,
            tolerance=int(settings.SYP_MATCH_TOLERANCE),
            window_minutes=240,
        )

        if matched:
            # ✅ موافقة مباشرة
            approve_topup(db, tx_id=tx.id)
            await state.clear()
            await message.answer(
                f"✅ تم شحن محفظتك تلقائياً بمبلغ <b>{amount_usd}</b> USD.\nرقم الطلب: {tx.id}",
                parse_mode="HTML"
            )
        else:
            # ❌ ما في تطابق → مراجعة الإدارة
            await state.clear()
            await message.answer(
                "⚠️ المعلومات غير متطابقة.\nتم تسجيل الطلب لمراجعة الإدارة.\n"
                f"المبلغ: <b>{amount_usd}</b> USD\n"
                f"رقم الطلب: {tx.id}",
                parse_mode="HTML"
            )
    finally:
        db.close()


@router.message(TopupFlow.waiting_usdt_amount)
async def usdt_amount_step(message: Message, state: FSMContext):
    if (message.text or "") in NAV_TEXTS:
        await state.clear()
        await message.answer("اختر من القائمة:", reply_markup=main_menu())
        return

    txt = message.text.replace(",", ".").strip()
    try:
        usd = Decimal(txt)
        if usd <= 0:
            raise InvalidOperation()
    except Exception:
        await message.answer("قيمة غير صالحة. أعد الإدخال مثل: 10 أو 10.50")
        return

    await state.update_data(amount_usd=str(usd))
    await state.set_state(TopupFlow.waiting_usdt_txid)

    db = db_session()
    try:
        data = await state.get_data()
        method = get_by_id(db, int(data["topup_method_id"]))
        details = method.details or {}
        address = details.get("address", "—")
        network = details.get("network", "—")

        is_sham_usd = bool(data.get("is_sham_usd"))

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_flow")]
        ])

        if is_sham_usd:
            await message.answer(
                f"أرسل <b>{usd}</b> USD\n"
                f"العنوان/الحساب: <code>{address}</code>\n"
                f"ثم أرسل <b>رقم العملية</b> هنا.",
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"أرسل <b>{usd}</b> USDT\n"
                f"العنوان: <code>{address}</code>\n"
                f"الشبكة: <b>{network}</b>\n"
                f"ثم أرسل TXID هنا.",
                reply_markup=kb,
                parse_mode="HTML"
            )
    finally:
        db.close()

@router.message(TopupFlow.waiting_usdt_txid)
async def usdt_txid_step(message: Message, state: FSMContext):
    db = db_session()
    try:
        u = get_by_tg_id(db, message.from_user.id)
        if not u:
            await message.answer("اكتب /start أولاً.")
            await state.clear(); return
        w = get_wallet_usd(db, u.id)
        if not w:
            await message.answer("لا توجد محفظة USD.")
            await state.clear(); return

        data = await state.get_data()
        method_id = int(data["topup_method_id"])
        amount_usd = Decimal(data["amount_usd"])
        txid = message.text.strip()
        is_sham_usd = bool(data.get("is_sham_usd"))

        if is_sham_usd:
            note = "sham_usd"
            admin_title = "Sham Cash (USD)"
            tx_label = "رقم العملية"
        else:
            note = "usdt"
            admin_title = "USDT"
            tx_label = "TXID"

        try:
            tx = create_pending_topup(
                db,
                wallet_id=w.id,
                topup_method_id=method_id,
                amount_usd=amount_usd,
                op_ref=txid,
                note=note,
            )
            await state.clear()
            await message.answer(
                f"تم تسجيل طلب الشحن بقيمة <b>{amount_usd}</b> USD.\n"
                f"الحالة: PENDING\nرقم الطلب: {tx.id}",
                parse_mode="HTML"
            )
        except DuplicateOperationRefError:
            await message.answer("خطأ: رقم العملية مستخدم من قبل. أدخل رقماً مختلفاً.")
            return

        admin_text = (
            f"📥 <b>طلب شحن جديد - {admin_title}</b>\n"
            f"👤 المستخدم: <b>{u.name}</b> (TG: <code>{u.tg_id}</code>)\n"
            f"💵 المبلغ: <b>{amount_usd} USD</b>\n"
            f"🔗 {tx_label}: <code>{txid}</code>\n"
            f"📌 رقم الطلب: <b>#{tx.id}</b>"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"adm_approve:{tx.id}"),
            InlineKeyboardButton(text="❌ رفض",    callback_data=f"adm_reject:{tx.id}")
        ]])

        bot = message.bot
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(admin_id, admin_text, reply_markup=kb)
    finally:
        db.close()
