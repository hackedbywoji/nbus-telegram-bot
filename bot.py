import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from playwright.async_api import async_playwright

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BUS_BONO = os.getenv('BUS_BONO')
BUS_PIN = os.getenv('BUS_PIN')
CORREO_USER = os.getenv('CORREO_USER')
CP_USER = os.getenv('CP_USER')
MI_TELEGRAM_ID = int(os.getenv('MI_TELEGRAM_ID', 0))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ZONA_ES = ZoneInfo("Europe/Madrid")


def resolver_fecha(dia: str) -> str:
    ahora = datetime.now(ZONA_ES)
    if dia == "hoy":
        return ahora.strftime('%Y-%m-%d')
    elif dia == "manana":
        return (ahora + timedelta(days=1)).strftime('%Y-%m-%d')
    return dia


def build_url(fecha: str, tipo_viaje: str) -> str:
    base = "https://comprasweb.interbus.es/venta/selection"
    corella = "Corella.%20%20C%2F%20Tajadas%205"
    corella_id = "Z10"
    corella_addr = "C%2F%20Tajadas,%20%205,%20Corella"
    tudela = "Tudela.%20%20Estaci%C3%B3n%20Bus.%20C%2F%20Cuesta%20Estaci%C3%B3n"
    tudela_id = "Z21"
    tudela_addr = "Estaci%C3%B3n%20Bus.%20%20C%2F%20Cuesta%20Estaci%C3%B3n,%20%20Tudela"
    comun = f"&passengers=1&fare_ids=01&genders=M&mode=0&schedules=false&locale=es-ES"

    if tipo_viaje == "vuelta":
        return (f"{base}?origin={tudela}&origin_id={tudela_id}&origin_address={tudela_addr}"
                f"&destination={corella}&destination_id={corella_id}&destination_address={corella_addr}"
                f"&journey_type=0&departure_time={fecha}{comun}")
    elif tipo_viaje == "idavuelta":
        return (f"{base}?origin={corella}&origin_id={corella_id}&origin_address={corella_addr}"
                f"&destination={tudela}&destination_id={tudela_id}&destination_address={tudela_addr}"
                f"&journey_type=1&departure_time={fecha}&return_time={fecha}{comun}")
    else:  # ida
        return (f"{base}?origin={corella}&origin_id={corella_id}&origin_address={corella_addr}"
                f"&destination={tudela}&destination_id={tudela_id}&destination_address={tudela_addr}"
                f"&journey_type=0&departure_time={fecha}{comun}")


async def automatizar_reserva(fecha: str, tipo_viaje: str, hora_ida: str | None, hora_vuelta: str | None, message):
    url = build_url(fecha, tipo_viaje)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context()).new_page()

        try:
            logger.info(f"Abriendo web para {fecha} ({tipo_viaje})...")
            await page.goto(url)

            try:
                btn = page.get_by_role("button", name="Denegar")
                await btn.wait_for(timeout=2000, state="visible")
                await btn.click()
            except Exception:
                pass

            if tipo_viaje == "ida":
                await page.locator("app-departure").filter(has_text=hora_ida).locator(".Button").first.click()
            elif tipo_viaje == "vuelta":
                await page.locator("app-departure").filter(has_text=hora_vuelta).locator(".Button").first.click()
            else:
                await page.locator("app-departure").filter(has_text=hora_ida).locator(".Button").first.click()
                await page.locator("app-departure").filter(has_text=hora_vuelta).locator(".Button").first.click()

            await page.get_by_role("button", name="Continuar").click()
            await page.get_by_role("button", name="Continuar").click()

            await page.get_by_role("textbox", name="Bono").fill(BUS_BONO)
            await page.get_by_role("textbox", name="Bono").press("Tab")
            await page.get_by_role("textbox", name="Pin").fill(BUS_PIN)
            await page.get_by_role("button", name="Aplicar").click()
            await page.wait_for_timeout(2000)

            await page.get_by_role("textbox", name="Repita correo *").fill(CORREO_USER)
            await page.locator("#countrycode").select_option("ES")
            await page.get_by_role("textbox", name="Código postal *").fill(CP_USER)
            await page.get_by_role("checkbox", name="He leído y acepto las").check()

            await page.get_by_role("button", name="Pagar").click()
            await page.wait_for_timeout(5000)

            await browser.close()
            return f"✅ Billete comprado, te llega a {CORREO_USER}"

        except Exception as e:
            logger.error(f"Error durante la compra: {e}")
            ts = datetime.now(ZONA_ES).strftime('%H%M%S')
            captura = f"error_{ts}.png"
            try:
                await page.screenshot(path=captura)
                await message.reply_photo(
                    photo=open(captura, 'rb'),
                    caption=f"❌ Algo falló en la web.\n\n{str(e)[:150]}"
                )
                os.remove(captura)
            except Exception as e2:
                logger.error(f"No se pudo hacer captura: {e2}")

            await browser.close()
            return "❌ Compra abortada, revisa el log."


def generar_teclado_buses(dia: str, tipo: str):
    ahora = datetime.now(ZONA_ES)
    limite = ahora + timedelta(minutes=20)

    horarios = {
        "ida":    ["7:13", "8:14", "10:00", "11:01", "12:16", "13:11", "14:31", "15:44", "17:25", "18:41", "20:01"],
        "vuelta": ["8:10", "9:10", "10:40", "11:40", "13:05", "13:50", "15:20", "16:18", "18:05", "19:15", "20:50"],
    }

    es_hoy = dia == "hoy" or dia == ahora.strftime('%Y-%m-%d')
    horas_validas = []

    for h in horarios[tipo]:
        if not es_hoy:
            horas_validas.append(h)
        else:
            hh, mm = map(int, h.split(':'))
            if ahora.replace(hour=hh, minute=mm, second=0, microsecond=0) > limite:
                horas_validas.append(h)

    teclado = []
    fila = []
    for h in horas_validas:
        label = h if len(h.split(':')[0]) == 2 else f"0{h}"
        cb = f"{dia}|{tipo}|{h}|none" if tipo == "ida" else f"{dia}|{tipo}|none|{h}"
        fila.append(InlineKeyboardButton(label, callback_data=cb))
        if len(fila) == 3:
            teclado.append(fila)
            fila = []
    if fila:
        teclado.append(fila)

    teclado.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{dia}|main")])
    return InlineKeyboardMarkup(teclado), len(horas_validas)


async def comando_pillar_bus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MI_TELEGRAM_ID:
        await update.message.reply_text("⛔️ Bot privado.")
        return

    teclado = [
        [InlineKeyboardButton("📅 HOY", callback_data="hoy|main")],
        [InlineKeyboardButton("📅 MAÑANA", callback_data="manana|main")],
        [InlineKeyboardButton("📆 Otro día...", callback_data="calendario|nada")],
    ]
    await update.message.reply_text("🚌 ¿Para cuándo?", reply_markup=InlineKeyboardMarkup(teclado))


async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != MI_TELEGRAM_ID:
        await query.answer("⛔️ Sin permiso.", show_alert=True)
        return

    await query.answer()
    datos = query.data.split("|")
    dia, accion = datos[0], datos[1]

    if dia == "inicio":
        teclado = [
            [InlineKeyboardButton("📅 HOY", callback_data="hoy|main")],
            [InlineKeyboardButton("📅 MAÑANA", callback_data="manana|main")],
            [InlineKeyboardButton("📆 Otro día...", callback_data="calendario|nada")],
        ]
        await query.edit_message_text("🚌 ¿Para cuándo?", reply_markup=InlineKeyboardMarkup(teclado))
        return

    if dia == "calendario":
        ahora = datetime.now(ZONA_ES)
        teclado = [
            [InlineKeyboardButton(
                f"🗓 {(ahora + timedelta(days=i)).strftime('%d/%m/%Y')}",
                callback_data=f"{(ahora + timedelta(days=i)).strftime('%Y-%m-%d')}|main"
            )]
            for i in range(2, 9)
        ]
        teclado.append([InlineKeyboardButton("🔙 Volver", callback_data="inicio|inicio")])
        await query.edit_message_text("📆 Elige fecha:", reply_markup=InlineKeyboardMarkup(teclado))
        return

    if accion == "main":
        texto_dia = "HOY" if dia == "hoy" else "MAÑANA" if dia == "manana" else dia
        teclado = [
            [InlineKeyboardButton("↔️ Ida y Vuelta (7:13 - 19:15)", callback_data=f"{dia}|idavuelta|7:13|19:15")],
            [InlineKeyboardButton("➡️ Solo Ida", callback_data=f"{dia}|menu_ida")],
            [InlineKeyboardButton("⬅️ Solo Vuelta", callback_data=f"{dia}|menu_vuelta")],
            [InlineKeyboardButton("🔙 Cambiar día", callback_data="inicio|inicio")],
        ]
        await query.edit_message_text(f"{texto_dia} — ¿qué necesitas?", reply_markup=InlineKeyboardMarkup(teclado))
        return

    if accion in ("menu_ida", "menu_vuelta"):
        tipo = accion.replace("menu_", "")
        markup, total = generar_teclado_buses(dia, tipo)
        emoji = "➡️" if tipo == "ida" else "⬅️"
        texto = (f"{emoji} Horarios de {'IDA' if tipo == 'ida' else 'VUELTA'} — {dia.upper()}:"
                 if total else "😢 No quedan buses disponibles para hoy.")
        await query.edit_message_text(texto, reply_markup=markup)
        return

    # reserva
    if len(datos) < 4:
        await query.edit_message_text("⚠️ Algo falló con los datos. Usa /pillarbus de nuevo.")
        return

    tipo_viaje = datos[1]
    hora_ida = datos[2] if datos[2] != "none" else None
    hora_vuelta = datos[3] if datos[3] != "none" else None
    fecha = resolver_fecha(dia)

    resumen = (
        f"ida {hora_ida}" if tipo_viaje == "ida"
        else f"vuelta {hora_vuelta}" if tipo_viaje == "vuelta"
        else f"ida {hora_ida} / vuelta {hora_vuelta}"
    )
    await query.edit_message_text(f"⚙️ Comprando billete ({resumen})...")

    resultado = await automatizar_reserva(fecha, tipo_viaje, hora_ida, hora_vuelta, query.message)
    await query.message.reply_text(resultado)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("pillarbus", comando_pillar_bus))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    logger.info("Bot arrancado. /pillarbus para empezar.")
    app.run_polling()


if __name__ == '__main__':
    main()