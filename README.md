# 🚌 NBUS Telegram Bot Automator

Un microservicio en Python diseñado para automatizar la reserva y compra dinámica de billetes de autobús diarios mediante web scraping asíncrono y Telegram API.

## 🚀 Objetivo del Proyecto
Eliminar la fricción de ejecutar tareas manuales y repetitivas en pasarelas web de transporte. Este bot permite gestionar reservas de rutas recurrentes en tiempo real y con solo 2 clics desde Telegram, interactuando de forma invisible con el DOM de la página oficial.

## ⚙️ Características Técnicas
* **Web Scraping Asíncrono:** Uso de `Playwright` para navegación rápida, evasión automática de modales (cookies) e inyección segura de credenciales de bonos de transporte.
* **Filtro Lógico en Tiempo Real:** El sistema lee la hora del servidor y purga dinámicamente los autobuses que ya han salido (o salen en menos de 20 min) para optimizar recursos y evitar errores de Timeout.
* **Manejo de Errores Visual:** Sistema de alerta integrado. Si la web destino cambia su estructura o se cae, el bot realiza una captura de pantalla *headless* en el momento exacto del fallo y la envía por Telegram para facilitar el debug.
* **Interfaz Interactiva:** Flujo de usuario estructurado mediante teclados en línea dinámicos (`InlineKeyboardMarkup`).
* **Preparado para Producción:** Código modular configurado para ejecutarse 24/7 en modo `headless` en entornos Cloud (Render) o infraestructura local (contenedores LXC en Proxmox).

## 🛠️ Stack Tecnológico
* **Lenguaje principal:** Python 3.x
* **Navegación / QA:** Playwright (async API)
* **Framework Bot:** `python-telegram-bot`
* **Gestión de entorno:** `python-dotenv`

## 🔐 Configuración (.env)
Para desplegar este servicio, se requiere un archivo `.env` en la raíz (ignorado por seguridad en este repositorio) con las siguientes variables:
```text
TELEGRAM_TOKEN=tu_token_aqui
BUS_BONO=tu_numero_de_bono
BUS_PIN=tu_pin_de_seguridad
