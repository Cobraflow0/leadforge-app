"""
Generador de páginas SEO programáticas — oficio x ciudad.

Genera una página estática por cada combinación de oficio (los 5 del
vertical construcción/reformas, ver memoria strategy_growth_plan_fable) y
ciudad, con un dato real (nº de profesionales de ese oficio ya detectados
en esa ciudad vía OpenStreetMap) como gancho honesto de "hay mucha
competencia, destaca contactando tú primero a tus clientes".

No depende de leadforge-prospector ni de leadforge-api — es un script
independiente, se ejecuta a mano cuando se quiera regenerar (los números
de competencia cambian poco, no hace falta automatizarlo).

Uso: python3 generate_seo_pages.py
Salida: leadforge-app/leads/{oficio}-{ciudad-slug}.html + sitemap.xml
"""

import json
import os
import re
import time
import unicodedata

import requests

HEADERS = {"User-Agent": "LeadForgeSEOGen/1.0 (contacto: hola@leadforge.es)"}

CIUDADES = [
    "Madrid, España", "Barcelona, España", "Valencia, España", "Sevilla, España",
    "Bilbao, España", "Málaga, España", "Zaragoza, España", "Murcia, España",
    "Palma de Mallorca, España", "Alicante, España", "Granada, España",
    "Córdoba, España", "Valladolid, España", "A Coruña, España",
    "San Sebastián, España", "Santander, España", "Salamanca, España",
    "Toledo, España", "Burgos, España", "Vigo, España",
]

OFICIOS = {
    "reformistas":  {"label": "reformas",      "singular": "empresa de reformas", "plural": "empresas de reformas", "articulo": "una", "tags": [("craft", "builder")]},
    "fontaneria":   {"label": "fontanería",    "singular": "fontanero",           "plural": "fontaneros",           "articulo": "un",  "tags": [("craft", "plumber")]},
    "electricidad": {"label": "electricidad",  "singular": "electricista",        "plural": "electricistas",        "articulo": "un",  "tags": [("craft", "electrician")]},
    "cerrajeria":   {"label": "cerrajería",    "singular": "cerrajero",           "plural": "cerrajeros",           "articulo": "un",  "tags": [("shop", "locksmith"), ("craft", "locksmith")]},
    "pintura":      {"label": "pintura",       "singular": "pintor",              "plural": "pintores",             "articulo": "un",  "tags": [("craft", "painter")]},
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "leads")
SITE_BASE = "https://leadforge.es"


def slugify(ciudad):
    nombre = ciudad.split(",")[0]
    nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    nombre = re.sub(r"[^a-zA-Z0-9]+", "-", nombre).strip("-").lower()
    return nombre


_area_cache = {}


def geocode_area(ciudad):
    if ciudad in _area_cache:
        return _area_cache[ciudad]
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": ciudad, "format": "json", "addressdetails": 1, "limit": 5},
            headers=HEADERS, timeout=15,
        )
        candidatos = r.json()
    except Exception as e:
        print(f"  [geocode] Error {ciudad}: {e}")
        _area_cache[ciudad] = None
        return None
    tipos_buenos = {"city", "town", "village", "municipality"}
    elegido = next((c for c in candidatos if c.get("osm_type") == "relation" and c.get("addresstype") in tipos_buenos), None)
    if not elegido:
        elegido = next((c for c in candidatos if c.get("osm_type") == "relation"), None)
    if not elegido:
        _area_cache[ciudad] = None
        return None
    area_id = 3600000000 + int(elegido["osm_id"])
    _area_cache[ciudad] = area_id
    time.sleep(1)
    return area_id


def count_osm(area_id, tags):
    filtros = "".join(f'node["{k}"="{v}"](area.a);way["{k}"="{v}"](area.a);' for k, v in tags)
    query = f'[out:json][timeout:50];area({area_id})->.a;({filtros});out count;'
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, headers=HEADERS, timeout=55)
        if r.status_code != 200:
            return None
        elements = r.json().get("elements", [])
        for el in elements:
            if el.get("type") == "count":
                tags_out = el.get("tags", {})
                return int(tags_out.get("total", 0))
    except Exception as e:
        print(f"  [overpass] Error: {e}")
    return None


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Consigue clientes de {label} en {ciudad_corta} | LeadForge</title>
<meta name="description" content="Encuentra automáticamente empresas que necesitan {label} en {ciudad_corta}. Más de {count} {singular_plural} ya compiten por los mismos clientes — destaca contactando tú primero.">
<link rel="canonical" href="{site_base}/leads/{slug}.html">
<style>
  body{{margin:0;padding:0;background:#f4f6f9;font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a2e;}}
  .wrap{{max-width:640px;margin:0 auto;padding:56px 20px;}}
  h1{{font-size:28px;line-height:1.3;margin:0 0 20px;}}
  p{{font-size:16px;line-height:1.7;color:#374151;margin:0 0 18px;}}
  .stat{{background:#fff;border-radius:10px;padding:20px 24px;margin:0 0 24px;box-shadow:0 2px 12px rgba(0,0,0,0.06);font-size:15px;}}
  .stat strong{{color:#0066FF;font-size:20px;}}
  .cta{{display:inline-block;background:#0066FF;color:#fff;text-decoration:none;font-weight:700;padding:14px 32px;border-radius:8px;margin-top:8px;}}
  .footer{{margin-top:40px;font-size:12px;color:#9ca3af;}}
</style>
</head>
<body>
<div class="wrap">
  <h1>¿Eres {articulo} {singular} en {ciudad_corta}? Consigue clientes nuevos sin depender solo del boca a boca</h1>
  <div class="stat">Solo en <strong>{ciudad_corta}</strong> hay más de <strong>{count}</strong> {singular_plural} compitiendo por los mismos clientes.</div>
  <p>La mayoría depende del boca a boca o de plataformas que se quedan con parte del margen — y pierde clientes potenciales cada semana porque no tiene tiempo de buscarlos uno a uno.</p>
  <p>LeadForge encuentra automáticamente las empresas que ya podrían necesitar tus servicios en {ciudad_corta} — nombre, email, teléfono y web reales — y te deja contactarlas con una campaña personalizada en minutos.</p>
  <p>A una empresa de reformas le conseguimos 1.309 leads cualificados de su sector y 3 clientes nuevos el primer día de campaña, sin llamadas en frío ni publicidad.</p>
  <a class="cta" href="{site_base}/app.html?utm_source=seo&amp;utm_campaign={slug}">Prueba LeadForge gratis →</a>
  <div class="footer">LeadForge · leadforge.es · Dato de competencia: OpenStreetMap, actualizado {fecha}.</div>
</div>
</body>
</html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    from datetime import date
    fecha = date.today().strftime("%d/%m/%Y")

    urls = []
    resultados = {}

    for ciudad in CIUDADES:
        area_id = geocode_area(ciudad)
        ciudad_corta = ciudad.split(",")[0]
        if not area_id:
            print(f"[SKIP] No se pudo geocodificar {ciudad}")
            continue
        for oficio_id, info in OFICIOS.items():
            count = count_osm(area_id, info["tags"])
            if count is None:
                time.sleep(3)  # el servidor público de Overpass a veces necesita más margen — un reintento
                count = count_osm(area_id, info["tags"])
            time.sleep(2.5)
            if count is None:
                print(f"  [SKIP] {oficio_id} en {ciudad_corta} — error de consulta (2 intentos)")
                continue
            if count == 0:
                print(f"  [SKIP] {oficio_id} en {ciudad_corta} — 0 resultados, página débil")
                continue
            slug = f"{oficio_id}-{slugify(ciudad)}"
            singular_plural = info["plural"]

            html = PAGE_TEMPLATE.format(
                label=info["label"], ciudad_corta=ciudad_corta, count=count,
                singular_plural=singular_plural, singular=info["singular"],
                articulo=info["articulo"], slug=slug, site_base=SITE_BASE, fecha=fecha,
            )
            with open(os.path.join(OUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            urls.append(f"{SITE_BASE}/leads/{slug}.html")
            resultados[slug] = count
            print(f"  [OK] {slug} -> {count} {singular_plural}")

    # sitemap.xml
    sitemap_path = os.path.join(OUT_DIR, "..", "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write(f"  <url><loc>{SITE_BASE}/app.html</loc></url>\n")
        for url in urls:
            f.write(f"  <url><loc>{url}</loc></url>\n")
        f.write("</urlset>\n")

    with open(os.path.join(OUT_DIR, "_datos_generacion.json"), "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "resultados": resultados}, f, ensure_ascii=False, indent=2)

    print(f"\nTotal páginas generadas: {len(urls)}")


if __name__ == "__main__":
    main()
