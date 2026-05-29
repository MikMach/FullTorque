"""Teste e2e (Playwright): no admin, escolher a Marca filtra os Modelos.

Corre contra um servidor local em http://127.0.0.1:8002.
    .venv/bin/python scripts/teste_filtro_modelo.py
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8002"
pedidos_autocomplete = []


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", lambda req: pedidos_autocomplete.append(req.url)
                if "/autocomplete/" in req.url else None)

        # --- login como dono ---
        page.goto(f"{BASE}/admin/login/")
        page.fill("#id_username", "dono@fulltorque.pt")
        page.fill("#id_password", "FullTorque2026")
        page.click("button[type=submit], input[type=submit]")
        page.wait_for_load_state("networkidle")
        print("após login, url:", page.url)

        page.goto(f"{BASE}/admin/oficina/viatura/add/")
        page.wait_for_load_state("networkidle")
        assert "/viatura/add/" in page.url, f"não chegou ao form (login falhou?): {page.url}"
        print("login OK, no formulário de viatura")

        def escolhe_marca(nome):
            page.click("#select2-id_marca-container")
            page.fill("input.select2-search__field", nome)
            page.wait_for_selector(f"li.select2-results__option:has-text('{nome}')", timeout=8000)
            page.click(f"li.select2-results__option:has-text('{nome}')")
            page.wait_for_timeout(300)

        def abre_modelo():
            pedidos_autocomplete.clear()
            page.click("#select2-id_modelo-container")
            page.wait_for_timeout(1500)  # deixa o ajax do select2 responder
            opts = []
            for o in page.query_selector_all("li.select2-results__option"):
                t = (o.inner_text() or "").strip()
                if t and "A procurar" not in t and "Searching" not in t:
                    opts.append(t)
            url = [u for u in pedidos_autocomplete if "field_name=modelo" in u]
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            return (url[-1] if url else None), opts

        print("\n--- Marca = Peugeot ---")
        escolhe_marca("Peugeot")
        url_p, opts_p = abre_modelo()
        print("pedido autocomplete:", url_p)
        print("modelos mostrados:", opts_p[:8], f"(total {len(opts_p)})")

        print("\n--- Marca = Volkswagen ---")
        escolhe_marca("Volkswagen")
        url_v, opts_v = abre_modelo()
        print("pedido autocomplete:", url_v)
        print("modelos mostrados:", opts_v[:8], f"(total {len(opts_v)})")

        browser.close()

        # --- verificações ---
        print("\n=== VERIFICAÇÕES ===")
        ok = True

        def checa(cond, msg):
            nonlocal ok
            print(("✅" if cond else "❌"), msg)
            ok = ok and cond

        checa(bool(url_p) and "marca=" in url_p, "pedido (Peugeot) inclui marca=")
        checa(any("Peugeot" in o for o in opts_p), "mostra modelos Peugeot")
        checa(not any("Volkswagen" in o for o in opts_p), "NÃO mostra Volkswagen ao escolher Peugeot")
        checa(any("Volkswagen" in o for o in opts_v), "mostra modelos Volkswagen")
        checa(not any("Peugeot" in o for o in opts_v), "NÃO mostra Peugeot ao escolher Volkswagen")
        print("\nRESULTADO:", "✅ FILTRO FUNCIONA" if ok else "❌ FALHOU")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
