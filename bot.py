import os
import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from playwright.async_api import async_playwright

load_dotenv()

# ==========================================
# 🔒 CREDENCIALES Y VARIABLES DE ENTORNO
# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BUS_BONO = os.getenv('BUS_BONO')
BUS_PIN = os.getenv('BUS_PIN')
CORREO_USER = os.getenv('CORREO_USER')
CP_USER = os.getenv('CP_USER')
MI_TELEGRAM_ID = int(os.getenv('MI_TELEGRAM_ID', 0)) 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ZONA_ES = ZoneInfo("Europe/Madrid")

# 1. FUNCIÓN DE SCRAPING CON PAGO INCLUIDO Y CAPTURAS DE ERROR
async def automatizar_reserva(query, tipo_viaje: str, hora_ida: str, hora_vuelta: str):
    datos_extraidos = query.data.split("|")
    dia_str = datos_extraidos[0]
    
    ahora = datetime.now(ZONA_ES)
    
    if dia_str == "hoy":
        fecha = ahora.strftime('%Y-%m-%d')
    elif dia_str == "manana":
        fecha = (ahora + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        fecha = dia_str 
    
    if tipo_viaje == "ida":
        url_directa = f"https://comprasweb.interbus.es/venta/selection?origin=Corella.%20%20C%2F%20Tajadas%205&origin_id=Z10&origin_address=C%2F%20Tajadas,%20%205,%20Corella&destination=Tudela.%20%20Estaci%C3%B3n%20Bus.%20C%2F%20Cuesta%20Estaci%C3%B3n&destination_id=Z21&destination_address=Estaci%C3%B3n%20Bus.%20%20C%2F%20Cuesta%20Estaci%C3%B3n,%20%20Tudela&journey_type=0&departure_time={fecha}&passengers=1&fare_ids=01&genders=M&mode=0&schedules=false&locale=es-ES"
    elif tipo_viaje == "vuelta":
        url_directa = f"https://comprasweb.interbus.es/venta/selection?origin=Tudela.%20%20Estaci%C3%B3n%20Bus.%20C%2F%20Cuesta%20Estaci%C3%B3n&origin_id=Z21&origin_address=Estaci%C3%B3n%20Bus.%20%20C%2F%20Cuesta%20Estaci%C3%B3n,%20%20Tudela&destination=Corella.%20%20C%2F%20Tajadas%205&destination_id=Z10&destination_address=C%2F%20Tajadas,%20%205,%20Corella&journey_type=0&departure_time={fecha}&passengers=1&fare_ids=01&genders=M&mode=0&schedules=false&locale=es-ES"
    else:
        url_directa = f"https://comprasweb.interbus.es/venta/selection?origin=Corella.%20%20C%2F%20Tajadas%205&origin_id=Z10&origin_address=C%2F%20Tajadas,%20%205,%20Corella&destination=Tudela.%20%20Estaci%C3%B3n%20Bus.%20C%2F%20Cuesta%20Estaci%C3%B3n&destination_id=Z21&destination_address=Estaci%C3%B3n%20Bus.%20%20C%2F%20Cuesta%20Estaci%C3%B3n,%20%20Tudela&journey_type=1&departure_time={fecha}&return_time={fecha}&passengers=1&fare_ids=01&genders=M&mode=0&schedules=false&locale=es-ES"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context()
        page = await context.new_page()

        try:
            logger.info(f"Cargando la plataforma para el {fecha}...")
            await page.goto(url_directa)
            
            try:
                btn_cookies = page.get_by_role("button", name="Denegar")
                await btn_cookies.wait_for(timeout=2000, state="visible") 
                await btn_cookies.click()
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

            logger.info("Rellenando campos de seguridad y aceptando términos...")
            await page.get_by_role("textbox", name="Repita correo *").fill(CORREO_USER)
            
            await page.locator("#countrycode").select_option("ES")
            await page.get_by_role("textbox", name="Código postal *").fill(CP_USER)
            
            await page.get_by_role("checkbox", name="He leído y acepto las").check()
            
            logger.info("Haciendo clic en PAGAR...")
            await page.get_by_role("button", name="Pagar").click()
            
            await page.wait_for_timeout(5000)
            
            await browser.close()
            return f"✅ ¡Compra finalizada! Billete emitido y enviado a {CORREO_USER}"
            
        except Exception as e:
            logger.error(f"Fallo detectado: {e}")
            ruta_captura = "error_pasarela.png"
            try:
                await page.screenshot(path=ruta_captura)
                await query.message.reply_photo(
                    photo=open(ruta_captura, 'rb'),
                    caption=f"❌ Error en la web.\n\n⚠️ Log: {str(e)[:150]}"
                )
                if os.path.exists(ruta_captura):
                    os.remove(ruta_captura)
            except Exception as e_screenshot:
                logger.error(f"Fallo de captura: {e_screenshot}")
                
            await browser.close()
            return "❌ Proceso abortado debido al fallo en la página."

# 2. FILTRADO DINÁMICO DE HORARIOS
def generar_teclado_buses(dia: str, tipo: str):
    ahora = datetime.now(ZONA_ES)
    limite = ahora + timedelta(minutes=20)
    
    if tipo == "ida":
        horas_todas = ["7:13", "8:14", "10:00", "11:01", "12:16", "13:11", "14:31", "15:44", "17:25", "18:41", "20:01"]
    else:
        horas_todas = ["8:10", "9:10", "10:40", "11:40", "13:05", "13:50", "15:20", "16:18", "18:05", "19:15", "20:50"]
        
    horas_validas = []
    
    es_hoy = (dia == "hoy" or dia == ahora.strftime('%Y-%m-%d'))
    
    for h in horas_todas:
        if not es_hoy:
            horas_validas.append(h)
        else:
            h_hour, h_min = map(int, h.split(':'))
            bus_time = ahora.replace(hour=h_hour, minute=h_min, second=0, microsecond=0)
            if bus_time > limite:
                horas_validas.append(h)
                
    teclado = []
    fila = []
    for h in horas_validas:
        texto_boton = h if len(h.split(':')[0]) == 2 else f"0{h}"
        callback = f"{dia}|{tipo}|{h}|nada" if tipo == "ida" else f"{dia}|{tipo}|nada|{h}"
        fila.append(InlineKeyboardButton(texto_boton, callback_data=callback))
        if len(fila) == 3:
            teclado.append(fila)
            fila = []
    if fila:
        teclado.append(fila)
        
    teclado.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{dia}|main")])
    return InlineKeyboardMarkup(teclado), len(horas_validas)

# 3. MENÚ INICIAL
async def comando_pillar_bus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MI_TELEGRAM_ID:
        await update.message.reply_text("⛔️ Acceso denegado. Este bot es de uso privado.")
        return

    teclado = [
        [InlineKeyboardButton("📅 Para HOY", callback_data="hoy|main")],
        [InlineKeyboardButton("📅 Para MAÑANA", callback_data="manana|main")],
        [InlineKeyboardButton("📆 Elegir otro día...", callback_data="calendario|nada")]
    ]
    await update.message.reply_text("🚌💨 ¿Para cuándo necesitas el billete?", reply_markup=InlineKeyboardMarkup(teclado))

# 4. GESTOR DE BOTONES INTERACTIVOS
async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id != MI_TELEGRAM_ID:
        await query.answer("⛔️ No tienes permiso para tocar esto.", show_alert=True)
        return

    await query.answer()
    
    datos = query.data.split("|")
    dia = datos[0]
    accion = datos[1]

    if dia == "inicio":
        teclado_inicio = [
            [InlineKeyboardButton("📅 Para HOY", callback_data="hoy|main")], 
            [InlineKeyboardButton("📅 Para MAÑANA", callback_data="manana|main")],
            [InlineKeyboardButton("📆 Elegir otro día...", callback_data="calendario|nada")]
        ]
        await query.edit_message_text("🚌💨 ¿Para cuándo necesitas el billete?", reply_markup=InlineKeyboardMarkup(teclado_inicio))
        return

    if dia == "calendario":
        teclado_calendario = []
        ahora = datetime.now(ZONA_ES)
        for i in range(2, 9):
            fecha_obj = ahora + timedelta(days=i)
            fecha_str = fecha_obj.strftime('%Y-%m-%d')
            fecha_mostrar = fecha_obj.strftime('%d/%m/%Y')
            teclado_calendario.append([InlineKeyboardButton(f"🗓 {fecha_mostrar}", callback_data=f"{fecha_str}|main")])
        
        teclado_calendario.append([InlineKeyboardButton("🔙 Volver", callback_data="inicio|inicio")])
        await query.edit_message_text("📆 Selecciona la fecha para tu billete:", reply_markup=InlineKeyboardMarkup(teclado_calendario))
        return

    if accion == "main":
        teclado_main = [
            [InlineKeyboardButton("Ida y Vuelta (7:13 - 19:15)", callback_data=f"{dia}|idavuelta|7:13|19:15")],
            [InlineKeyboardButton("Solo Ida ➡️", callback_data=f"{dia}|menu_ida")],
            [InlineKeyboardButton("Solo Vuelta ⬅️", callback_data=f"{dia}|menu_vuelta")],
            [InlineKeyboardButton("🔙 Cambiar de día", callback_data="inicio|inicio")]
        ]
        texto_dia = "HOY" if dia == "hoy" else "MAÑANA" if dia == "manana" else dia
        await query.edit_message_text(f"Ruta para {texto_dia}. ¿Qué necesitas?", reply_markup=InlineKeyboardMarkup(teclado_main))
        return

    elif accion == "menu_ida":
        markup, total = generar_teclado_buses(dia, "ida")
        if total == 0:
            await query.edit_message_text("😢 Ya no quedan buses de ida disponibles para hoy.", reply_markup=markup)
        else:
            await query.edit_message_text(f"➡️ Horas de IDA disponibles ({dia.upper()}):", reply_markup=markup)
        return

    elif accion == "menu_vuelta":
        markup, total = generar_teclado_buses(dia, "vuelta")
        if total == 0:
            await query.edit_message_text("😢 Ya no quedan buses de vuelta disponibles para hoy.", reply_markup=markup)
        else:
            await query.edit_message_text(f"⬅️ Horas de VUELTA disponibles ({dia.upper()}):", reply_markup=markup)
        return

    else:
        tipo_viaje = datos[1]
        hora_ida = datos[2]
        hora_vuelta = datos[3]
        
        texto_estado = f"Solo Ida ({hora_ida})" if tipo_viaje == "ida" else f"Solo Vuelta ({hora_vuelta})" if tipo_viaje == "vuelta" else f"Ida ({hora_ida}) y Vuelta ({hora_vuelta})"
        await query.edit_message_text(f"⚙️ Procesando ({dia.upper()}): {texto_estado}...")
        
        resultado = await automatizar_reserva(query, tipo_viaje, hora_ida, hora_vuelta)
        await query.message.reply_text(resultado)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("pillarbus", comando_pillar_bus))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    logger.info("Bot listo para producción. Manda /pillarbus")
    app.run_polling()

if __name__ == '__main__':
    main()