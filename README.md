# 🚌 NBUS Telegram Bot Automator

Un microservicio en Python diseñado para automatizar la reserva y compra dinámica de billetes de autobús mediante web scraping asíncrono y la API de Telegram.

## 🚀 Objetivo del Proyecto

Eliminar la fricción de ejecutar tareas manuales y repetitivas en pasarelas web de transporte. Este bot permite gestionar reservas de rutas recurrentes en tiempo real y con un par de clics desde Telegram, interactuando de forma totalmente invisible (*headless*) con el DOM de la página oficial.

## ⚙️ Características Técnicas

* **Web Scraping Asíncrono:** Uso de `Playwright` para navegación rápida, evasión automática de modales (cookies) e inyección segura de credenciales de pago.
* **Filtro Lógico en Tiempo Real:** El sistema lee la hora del servidor y purga dinámicamente los autobuses que ya han salido (o que salen en menos de 20 min) para optimizar recursos y evitar errores de *Timeout*.
* **Selección de Fechas Dinámica (V2):** Menú interactivo con calendario integrado para reservar billetes para el día en curso o con hasta 7 días de antelación.
* **Manejo de Errores Visual:** Sistema de alerta integrado. Si la web destino cambia su estructura o se cae, el bot realiza una captura de pantalla *headless* en el momento exacto del fallo y la envía por Telegram para facilitar la depuración.
* **Despliegue Contenerizado:** Código modular configurado y optimizado para ejecutarse 24/7 de forma aislada mediante contenedores **Docker**, garantizando estabilidad en entornos Cloud o infraestructura local.

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python 3.9+
* **Navegación / QA:** Playwright (Async API)
* **Framework Bot:** `python-telegram-bot`
* **Despliegue:** Docker

## 🔐 Configuración y Seguridad

Para desplegar este servicio, se requiere un archivo `.env` en la raíz del proyecto.

```env
TELEGRAM_TOKEN=tu_token_aqui
BUS_BONO=tu_numero_de_bono
BUS_PIN=tu_pin_de_seguridad

```

## 🐳 Despliegue en Producción (Docker)

La forma recomendada y más estable de ejecutar este bot es mediante Docker, ya que gestiona automáticamente los binarios de Chromium necesarios para Playwright.

1. **Construir la imagen:**
```bash
docker build -t nbus-bot .

```


2. **Ejecutar el contenedor en segundo plano (con reinicio automático):**
```bash
docker run -d --name nbus-bot --env-file .env --restart unless-stopped nbus-bot

```



## 💻 Desarrollo Local

Si deseas realizar pruebas o modificaciones rápidas en tu entorno local sin Docker:

1. Instalar dependencias:
```bash
pip install -r requirements.txt

```


2. Instalar binarios del navegador:
```bash
playwright install chromium

```


3. Ejecutar el servicio:
```bash
python bot.py

```
