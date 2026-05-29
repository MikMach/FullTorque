"""Teste e2e do filtro Marca->Modelo no INLINE de viaturas (página do Cliente)."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8002"
CLIENTE_ID = sys.argv[1]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url) if "/autocomplete/" in r.url else None)

    pg.goto(f"{BASE}/admin/login/")
    pg.fill("#id_username", "dono@fulltorque.pt")
    pg.fill("#id_password", "FullTorque2026")
    pg.click("button[type=submit], input[type=submit]")
    pg.wait_for_load_state("networkidle")

    pg.goto(f"{BASE}/admin/oficina/cliente/{CLIENTE_ID}/change/")
    pg.wait_for_load_state("networkidle")

    # Confirma que há pelo menos a linha 0 do inline de viaturas
    assert pg.query_selector("#select2-id_viaturas-0-marca-container"), "sem linha de inline de viatura"

    # Muda a marca da linha 0 para Peugeot
    pg.click("#select2-id_viaturas-0-marca-container")
    pg.fill("input.select2-search__field", "Peugeot")
    pg.wait_for_selector("li.select2-results__option:has-text('Peugeot')", timeout=8000)
    pg.click("li.select2-results__option:has-text('Peugeot')")
    pg.wait_for_timeout(400)

    # Abre o modelo da linha 0
    reqs.clear()
    pg.click("#select2-id_viaturas-0-modelo-container")
    pg.wait_for_timeout(1500)
    opts = []
    for o in pg.query_selector_all("li.select2-results__option"):
        t = (o.inner_text() or "").strip()
        if t and "rocura" not in t and "Searching" not in t:
            opts.append(t)
    url = [u for u in reqs if "field_name=modelo" in u]

    print("inline pedido autocomplete:", url[-1] if url else None)
    print("inline modelos mostrados:", opts[:6], f"(total {len(opts)})")
    ok = (bool(url) and "marca=" in (url[-1] or "")
          and any("Peugeot" in o for o in opts)
          and not any("Volkswagen" in o for o in opts))
    print("RESULTADO INLINE:", "✅ OK" if ok else "❌ FALHOU")
    b.close()
    sys.exit(0 if ok else 1)
