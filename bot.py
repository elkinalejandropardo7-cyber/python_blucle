import time
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "./whatsapp_session"

PHONE_NUMBER = "573229479546"
MESSAGE_TEXT = "Soy un bot de prueba , este mensaje se enviará automáticamente cada 10 segundos hasta que el destinatario responda. ¡Gracias por tu paciencia!"
INTERVAL_SECONDS = 10
CHECK_FREQUENCY = 5


def get_last_message(page):
    """Devuelve (id, es_entrante, ultimos_ids) del último mensaje del chat."""
    return page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[data-id]'));
            const ids = rows.map(e => e.getAttribute('data-id'));
            if (!rows.length) return [null, false, ids.slice(-4)];
            const last = rows[rows.length - 1];
            const id = last.getAttribute('data-id') || '';
            // Los mensajes enviados por nosotros tienen ticks (msg-check, msg-dblcheck, msg-time)
            const hasTicks = !!last.querySelector('[data-icon^="msg-"]');
            // Los enviados desde WhatsApp Web (el bot) empiezan con 3EB0
            const sentByBot = id.startsWith('3EB0');
            const incoming = !hasTicks && !sentByBot;
            return [id, incoming, ids.slice(-4)];
        }
    """)


def run_followup_loop():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = browser.new_page()

        page.goto("https://web.whatsapp.com")
        print("\n" + "=" * 50)
        print("1. Si aparece el código QR, escanéalo con tu celular.")
        print("2. Espera a que carguen tus chats en la pantalla.")
        input("3. Cuando veas tus chats listos, PRESIONA ENTER AQUÍ EN LA TERMINAL...")
        print("=" * 50 + "\n")

        print(f"Abriendo conversación con: {PHONE_NUMBER}...")
        page.goto(f"https://web.whatsapp.com/send?phone={PHONE_NUMBER}")

        chat_input = page.locator('footer div[contenteditable="true"]').first
        print("Esperando a que cargue el cuadro de texto del chat...")
        chat_input.wait_for(state="visible", timeout=60000)
        time.sleep(3)

        # Último mensaje al iniciar: si ya era entrante, no cuenta como respuesta nueva
        start_id, _, _ = get_last_message(page)
        print(f"Chat cargado. Último mensaje inicial: {start_id}")

        def respondieron():
            last_id, incoming, last_ids = get_last_message(page)
            print(f"  Últimos IDs: {last_ids} | entrante: {incoming}")
            return incoming and last_id != start_id

        try:
            while True:
                chat_input.click()
                chat_input.fill(MESSAGE_TEXT)
                chat_input.press("Enter")
                print(f"[{time.strftime('%H:%M:%S')}] Mensaje enviado. Esperando respuesta...")

                responded = False
                deadline = time.time() + INTERVAL_SECONDS
                while time.time() < deadline:
                    page.wait_for_timeout(CHECK_FREQUENCY * 1000)
                    if respondieron():
                        responded = True
                        break

                if responded:
                    print("¡El destinatario respondió! Deteniendo...")
                    break

        except KeyboardInterrupt:
            print("\nDetenido manualmente.")
        finally:
            print("Cerrando navegador...")
            browser.close()


if __name__ == "__main__":
    run_followup_loop()