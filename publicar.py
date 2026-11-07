#!/usr/bin/env python3
"""Toma la siguiente palabra, genera su Reel y lo publica en Instagram.

Variables de entorno:
  IG_TOKEN        token de la API de Instagram
  VIDEO_URL_BASE  URL pública de la carpeta del video (la pone el flujo de GitHub)
  SOLO_GENERAR=1  genera el video sin publicar
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import generar

RAIZ = Path(__file__).resolve().parent
API = "https://graph.instagram.com/v23.0"
ESTADO = RAIZ / "publicados.json"


def llamar(metodo, ruta, **datos):
    datos["access_token"] = os.environ["IG_TOKEN"]
    cuerpo = urllib.parse.urlencode(datos)
    url = f"{API}/{ruta}"
    if metodo == "GET":
        req = urllib.request.Request(f"{url}?{cuerpo}")
    else:
        req = urllib.request.Request(url, data=cuerpo.encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # El mensaje de Meta nunca incluye el token; la URL sí, por eso no se imprime
        sys.exit(f"Instagram respondió {e.code}: {e.read().decode()[:600]}")


def texto(e, config, dia):
    return (
        f"Día {dia}: {e['palabra']}. {e['remate']}\n\n"
        f"Si el origen no está comprobado, te lo decimos. Fuentes: {e['fuentes']}.\n\n"
        f"¿Qué palabra sigue? Dejala en los comentarios.\n\n{config['hashtags']}"
    )


def siguiente():
    hechos = json.loads(ESTADO.read_text()) if ESTADO.exists() else []
    palabras = json.loads((RAIZ / "guiones.json").read_text(encoding="utf-8"))
    pendientes = [i for i in range(len(palabras)) if palabras[i]["palabra"] not in hechos]
    if not pendientes:
        sys.exit("No quedan guiones nuevos en guiones.json")
    return pendientes[0], hechos, len(pendientes) - 1


def main():
    i, hechos, quedan = siguiente()
    nombre = f"dia-{i + 1:03d}.mp4"
    e, _ = generar.generar(i, RAIZ / "salida" / nombre)
    print(f"Generado {nombre}: {e['palabra']} (quedan {quedan})")
    if os.environ.get("SOLO_GENERAR") == "1":
        return
    config = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    url = os.environ["VIDEO_URL_BASE"].rstrip("/") + "/" + nombre
    ig_id = llamar("GET", "me", fields="user_id")["user_id"]
    contenedor = llamar(
        "POST", f"{ig_id}/media", media_type="REELS", video_url=url,
        caption=texto(e, config, i + 1), share_to_feed="true", thumb_offset="1500",
        is_ai_generated="true",
    )["id"]
    for _ in range(10):
        time.sleep(30)
        estado = llamar("GET", contenedor, fields="status_code")["status_code"]
        print("Estado:", estado)
        if estado == "FINISHED":
            break
        if estado in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram rechazó el video: {estado}")
    else:
        sys.exit("Instagram tardó demasiado en procesar el video")
    llamar("POST", f"{ig_id}/media_publish", creation_id=contenedor)
    hechos.append(e["palabra"])
    ESTADO.write_text(json.dumps(hechos, ensure_ascii=False, indent=1))
    print("Publicado:", e["palabra"])


if __name__ == "__main__":
    main()
