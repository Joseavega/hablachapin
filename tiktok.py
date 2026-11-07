#!/usr/bin/env python3
"""Sube el video del día a la bandeja de TikTok como borrador.

Uso:
  python tiktok.py autorizar   cambia TIKTOK_CODE por tokens y guarda el refresh token
  python tiktok.py subir FILE  renueva el acceso y sube FILE como borrador

Variables de entorno: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
(o TIKTOK_CODE para autorizar), GH_TOKEN y GH_REPO para guardar el refresh token nuevo.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://open.tiktokapis.com/v2"
REDIRECT_URI = "https://github.com/Joseavega/hablachapin"


def pedir(metodo, url, datos=None, headers=None, form=False):
    headers = dict(headers or {})
    cuerpo = None
    if datos is not None:
        if form:
            cuerpo = urllib.parse.urlencode(datos).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(datos, bytes):
            cuerpo = datos
        else:
            cuerpo = json.dumps(datos).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(url, data=cuerpo, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        sys.exit(f"TikTok respondió {e.code}: {e.read().decode()[:600]}")
    return json.loads(texto) if texto.strip().startswith("{") else {}


def tokens(**extra):
    datos = {
        "client_key": os.environ["TIKTOK_CLIENT_KEY"].strip(),
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"].strip(),
        **extra,
    }
    r = pedir("POST", f"{API}/oauth/token/", datos, form=True)
    if "access_token" not in r:
        # Nunca se imprime ningún token, solo el error
        detalle = {k: r.get(k) for k in ("error", "error_description", "log_id")}
        sys.exit(f"TikTok no entregó el acceso: {detalle}")
    if "video.upload" not in r.get("scope", ""):
        sys.exit("La autorización no incluye el permiso video.upload")
    return r["access_token"], r["refresh_token"]


def guardar_refresh(refresh):
    """Guarda el refresh token en los secretos del repositorio (TikTok puede cambiarlo)."""
    print(f"::add-mask::{refresh}")
    subprocess.run(["gh", "secret", "set", "TIKTOK_REFRESH_TOKEN", "--body", refresh], check=True)


def autorizar():
    codigo = os.environ["TIKTOK_CODE"].strip()
    # Acepta el código solo o la dirección completa copiada de la barra
    if "code=" in codigo:
        codigo = urllib.parse.parse_qs(urllib.parse.urlparse(codigo).query or codigo.split("?", 1)[-1])["code"][0]
    else:
        codigo = urllib.parse.unquote(codigo.split("&")[0])
    _, refresh = tokens(code=codigo, grant_type="authorization_code", redirect_uri=REDIRECT_URI)
    guardar_refresh(refresh)
    print("TikTok autorizado. Ya podés borrar el secreto TIKTOK_CODE.")


def subir(ruta):
    viejo = os.environ["TIKTOK_REFRESH_TOKEN"].strip()
    acceso, refresh = tokens(grant_type="refresh_token", refresh_token=viejo)
    if refresh != viejo:
        guardar_refresh(refresh)
    datos = Path(ruta).read_bytes()
    total = len(datos)
    auth = {"Authorization": f"Bearer {acceso}"}
    r = pedir(
        "POST", f"{API}/post/publish/inbox/video/init/",
        {"source_info": {"source": "FILE_UPLOAD", "video_size": total, "chunk_size": total, "total_chunk_count": 1}},
        auth,
    )
    if r.get("error", {}).get("code") != "ok":
        sys.exit(f"TikTok rechazó el borrador: {r.get('error')}")
    pedir(
        "PUT", r["data"]["upload_url"], datos,
        {"Content-Type": "video/mp4", "Content-Length": str(total), "Content-Range": f"bytes 0-{total - 1}/{total}"},
    )
    publish_id = r["data"]["publish_id"]
    for _ in range(12):
        time.sleep(10)
        s = pedir("POST", f"{API}/post/publish/status/fetch/", {"publish_id": publish_id}, auth)
        estado = s.get("data", {}).get("status")
        print("Estado en TikTok:", estado)
        if estado in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            print("Borrador enviado a la bandeja de TikTok.")
            return
        if estado == "FAILED":
            sys.exit(f"TikTok no pudo procesar el video: {s.get('data', {}).get('fail_reason')}")
    print("TikTok sigue procesando el video; debería llegar a la bandeja en unos minutos.")


if __name__ == "__main__":
    if sys.argv[1] == "autorizar":
        autorizar()
    else:
        subir(sys.argv[2])
