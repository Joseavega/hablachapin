#!/usr/bin/env python3
"""Convierte un guion de guiones.json en un Reel narrado y animado.

Uso: python generar.py <indice> [salida.mp4]
     python generar.py <indice> --cuadros t1,t2,...  (solo imágenes de prueba)
La voz (Kokoro) corre en la misma máquina y no usa servicios externos.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import skia

from ilustraciones import L, PROPS

RAIZ = Path(__file__).resolve().parent
ANCHO, ALTO, FPS = 1080, 1920, 30
MARGEN = 90
ANCHO_TEXTO = ANCHO - MARGEN - 140
TEXTO_Y0, TEXTO_Y1 = 1015, 1470  # dentro de la zona segura de Reels
ILU_X, ILU_Y, ILU_R = 520, 650, 340
SECCIONES = [
    ("intro", ""),
    ("origen", "DE DÓNDE VIENE"),
    ("historia", "UN POCO DE HISTORIA"),
    ("uso", "CÓMO LA USAMOS HOY"),
    ("remate", ""),
    ("cierre", ""),
]
PAUSA = 0.35
ENTRA_PALABRA = 0.22
SR = 44100
UNIDADES = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince".split()

# fondo, tinta, acento, segundo acento
PALETAS = [
    (0xFF0B6E4F, 0xFFFFF6E5, 0xFFFFC233, 0xFFE5277B),  # quetzal
    (0xFFC2185B, 0xFFFFF6E5, 0xFFFFD23F, 0xFF16B5A8),  # magenta
    (0xFF1F3FA8, 0xFFFFF6E5, 0xFFFF8A1F, 0xFFF4D35E),  # añil
    (0xFFF2A900, 0xFF22130A, 0xFFB3122C, 0xFF0B6E4F),  # flor de muerto
    (0xFFB3261E, 0xFFFFF6E5, 0xFFFFC233, 0xFF1BB6C9),  # grana
    (0xFF2A1458, 0xFFFFF6E5, 0xFFFF6FB5, 0xFF2BD9A8),  # noche
    (0xFF4FB3E8, 0xFF22130A, 0xFFB3122C, 0xFFFFD23F),  # cielo
]


def _fuente(nombre, cache={}):
    def f(tam):
        clave = (nombre, tam)
        if clave not in cache:
            tf = skia.Typeface.MakeFromFile(str(RAIZ / "fuentes" / nombre))
            fu = skia.Font(tf, tam)
            fu.setEdging(skia.Font.Edging.kAntiAlias)
            fu.setSubpixel(True)
            cache[clave] = fu
        return cache[clave]

    return f


FUENTES = {"negra": _fuente("ArchivoBlack.ttf"), "bold": _fuente("Poppins-Bold.ttf")}


def rebote(x):
    """Entrada con sobrepaso, para que las cosas caigan con peso."""
    x = min(1, max(0, x))
    s = 2.2
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def suave(x):
    x = min(1, max(0, x))
    return 1 - (1 - x) ** 3


def numero(n):
    """Número en letras para que la voz diga «día treinta y dos»."""
    if n < 16:
        return UNIDADES[n]
    if n < 20:
        return "dieci" + UNIDADES[n - 10]
    if n == 20:
        return "veinte"
    if n < 30:
        return "veinti" + UNIDADES[n - 20]
    dec = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
    if n < 100:
        return dec[n // 10] + (f" y {UNIDADES[n % 10]}" if n % 10 else "")
    if n == 100:
        return "cien"
    cen = ["", "ciento", "doscientos", "trescientos", "cuatrocientos"]
    return f"{cen[n // 100]} {numero(n % 100)}".strip()


def trozos(texto, maximo=46):
    """Parte la narración en frases cortas: por punto, por coma y, si no, por largo."""
    salida = []
    for frase in re.findall(r"[^.?!:]+[.?!:]*", texto):
        frase = frase.strip()
        if not frase:
            continue
        actual = ""
        for parte in re.split(r"(?<=,)\s+", frase):
            if actual and len(actual) + len(parte) + 1 > maximo:
                salida.append(actual)
                actual = ""
            for w in parte.split():
                if actual and len(actual) + len(w) + 1 > maximo:
                    salida.append(actual)
                    actual = w
                else:
                    actual = f"{actual} {w}".strip()
        if actual:
            salida.append(actual)
    return salida


def limpia(w):
    return re.sub(r"[^\wáéíóúüñ]", "", w.lower())


class Plan:
    """Línea de tiempo: secciones, frases, palabras e ilustraciones."""

    def __init__(self, g, dia, tiempos):
        self.g, self.dia = g, dia
        self.palabra = g["palabra"]
        destacar = {limpia(w) for w in g.get("destacar", [])} | {limpia(g["palabra"])}
        self.frases, self.secciones = [], []
        t = 0.0
        # Los datos: la gente se iba en la intro larga. Ahora arranca con el gancho y la palabra,
        # y lo del millón queda como cierre.
        cierre_txt = [f"Día {dia}, de camino a 1 millón de seguidores.", "Seguime para la palabra de mañana."]
        for i, ((clave, nombre), dur) in enumerate(zip(SECCIONES, tiempos)):
            if clave == "intro":
                partes = trozos(gancho(g), 52)
            elif clave == "cierre":
                partes = [q for p in cierre_txt for q in trozos(p, 52)]
            else:
                partes = trozos(g[clave])
            paleta = PALETAS[(dia * 3 + i * 2 + (i > 2)) % len(PALETAS)]
            self.secciones.append(dict(clave=clave, nombre=nombre, t0=t, t1=t + dur, paleta=paleta))
            total = sum(len(p) + 4 for p in partes)
            ilus = g["ilus"].get(clave, [])
            cursor = t
            for k, p in enumerate(partes):
                d = (dur - PAUSA) * (len(p) + 4) / total
                palabras, acum = [], 0
                carac = sum(len(w) + 1 for w in p.split())
                for w in p.split():
                    palabras.append(
                        dict(w=w, t0=cursor + (d * 0.94) * acum / carac, dest=self._dest(w, destacar))
                    )
                    acum += len(w) + 1
                nombre_ilu = ilus[min(k, len(ilus) - 1)] if ilus else None
                if clave == "intro":
                    nombre_ilu = "__pop__"
                elif clave == "cierre":
                    nombre_ilu = "__contador__"
                self.frases.append(
                    dict(t0=cursor, t1=cursor + d, palabras=palabras, ilu=nombre_ilu, seccion=i, texto=p)
                )
                cursor += d
            self.frases[-1]["t1"] = t + dur
            t += dur
        self.frases[-1]["t1"] = t + 1.0
        self.secciones[-1]["t1"] = t + 1.0
        self.duracion = t + 1.0
        # Cada ilustración cuenta su tiempo desde que aparece
        previa = None
        for f in self.frases:
            f["ilu_t0"] = previa["ilu_t0"] if previa and previa["ilu"] == f["ilu"] else f["t0"]
            previa = f
        # La palabra ya está completa en el primer cuadro (y en la miniatura)
        for f in self.frases:
            if f["ilu"] == "__pop__":
                f["ilu_t0"] = -0.4

    @staticmethod
    def _dest(w, destacar):
        l = limpia(w)
        return l in destacar or any(l.startswith(d) and len(d) > 3 and len(l) - len(d) <= 2 for d in destacar)

    def en(self, t):
        sec = next((i for i, s in enumerate(self.secciones) if t < s["t1"]), len(self.secciones) - 1)
        fr = next((i for i, f in enumerate(self.frases) if t < f["t1"]), len(self.frases) - 1)
        return sec, fr


def maquetar(palabras, ancho, tam, fuente):
    interlinea, espacio = tam * 1.2, tam * 0.3
    x, y, lineas = 0, 0, [[]]
    for p in palabras:
        a = fuente.measureText(p["w"])
        if x and x + a > ancho:
            x, y = 0, y + interlinea
            lineas.append([])
        lineas[-1].append((p, x, y, a))
        x += a + espacio
    return lineas, y + interlinea


def medir(frase, familia):
    for tam in range(104, 47, -4):
        fuente = familia(tam)
        _, alto = maquetar(frase["palabras"], ANCHO_TEXTO, tam, fuente)
        if alto <= TEXTO_Y1 - TEXTO_Y0 and all(fuente.measureText(p["w"]) <= ANCHO_TEXTO for p in frase["palabras"]):
            return tam
    raise ValueError(f"No cabe: {frase['texto']}")


class Render:
    def __init__(self, plan, cuenta):
        self.plan, self.cuenta = plan, cuenta
        self.sup = skia.Surface(ANCHO, ALTO)
        self.c = self.sup.getCanvas()
        self.l = L(self.c)
        self.p = skia.Paint(AntiAlias=True)
        for f in plan.frases:
            f["tam"] = medir(f, FUENTES["negra" if f["seccion"] == 4 else "bold"])
        rng = np.random.default_rng(plan.dia)
        self.chispas = [
            (rng.uniform(0, ANCHO), rng.uniform(-300, 0), rng.uniform(-90, 90), rng.uniform(320, 720),
             rng.uniform(0, 360), int(rng.integers(0, 3)))
            for _ in range(50)
        ]

    def fondo(self, sec, t):
        s = self.plan.secciones[sec]
        c = self.c
        if sec == 0 or t - s["t0"] > 0.5:
            c.clear(s["paleta"][0])
            return
        c.clear(self.plan.secciones[sec - 1]["paleta"][0])
        r = 2100 * suave((t - s["t0"]) / 0.5)
        self.p.setColor(s["paleta"][2])
        c.drawCircle(ILU_X, ILU_Y, r + 70, self.p)
        self.p.setColor(s["paleta"][0])
        c.drawCircle(ILU_X, ILU_Y, r, self.p)

    def aura(self, pal, t):
        c = self.c
        self.p.setColor(pal[1])
        self.p.setAlphaf(0.16)
        c.drawCircle(ILU_X, ILU_Y, ILU_R + 16 * math.sin(t * 2.6), self.p)
        self.p.setAlphaf(1)

    def banda(self, pal, y, t, sentido):
        c = self.c
        self.p.setColor(pal[3])
        c.drawRect(skia.Rect.MakeXYWH(0, y, ANCHO, 76), self.p)
        paso = 96
        d = (t * 90 * sentido) % paso
        for i in range(-1, 13):
            x = i * paso + d
            for color, m, a in ((pal[2] if i % 2 else pal[1], 38, 34), (pal[0], 18, 17)):
                self.p.setColor(color)
                r = skia.Path()
                cx, cy = x + 38, y + 38
                r.addPoly([skia.Point(cx - m, cy), skia.Point(cx, cy - a), skia.Point(cx + m, cy), skia.Point(cx, cy + a)], True)
                c.drawPath(r, self.p)

    def encabezado(self, pal):
        c = self.c
        fu = FUENTES["negra"](58)
        txt = f"DÍA {self.plan.dia}"
        a = fu.measureText(txt)
        self.p.setColor(pal[2])
        c.drawRoundRect(skia.Rect.MakeXYWH(MARGEN, 225, a + 56, 92), 26, 26, self.p)
        self.p.setColor(pal[0])
        c.drawString(txt, MARGEN + 28, 292, fu, self.p)

    def contador(self, pal, t, f):
        """El reto: del 0 hasta el millón."""
        c = self.c
        n = int((suave(min(1, (t - f["t0"]) / 2.4)) ** 3) * 1_000_000)
        s = f"{n:,}"
        fu = FUENTES["negra"](132 if len(s) > 7 else 170)
        a = fu.measureText(s)
        e = 1 + 0.05 * math.sin(t * 12)
        c.save()
        c.translate(ILU_X, ILU_Y)
        c.scale(e, e)
        self.p.setColor(pal[2])
        c.drawString(s, -a / 2, 40, fu, self.p)
        fu2 = FUENTES["bold"](58)
        self.p.setColor(pal[1])
        c.drawString("seguidores", -fu2.measureText("seguidores") / 2, 125, fu2, self.p)
        c.restore()

    def ilustracion(self, f, pal, t):
        c = self.c
        tl = t - f["ilu_t0"]
        if f["ilu"] == "__contador__":
            self.contador(pal, t, next(x for x in self.plan.frases if x["ilu"] == "__contador__"))
        elif f["ilu"] == "__pop__":
            c.save()
            c.translate(ILU_X, ILU_Y)
            c.rotate(-4 + 3 * math.sin(t * 5))
            e = rebote(tl / 0.35)
            c.scale(e, e)
            s = self.plan.palabra.upper()
            tam = 220
            while FUENTES["negra"](tam).measureText(s) > 860:
                tam -= 8
            fu = FUENTES["negra"](tam)
            self.p.setColor(pal[2])
            c.drawString(s, -fu.measureText(s) / 2, tam * 0.36, fu, self.p)
            c.restore()
        elif f["ilu"]:
            e = rebote(tl / 0.42)
            c.save()
            c.translate(ILU_X, ILU_Y + 12 * math.sin(t * 2.1))
            c.scale(e, e)
            PROPS[f["ilu"]](self.l, tl, pal, FUENTES)
            c.restore()

    def texto(self, f, pal, t, sec):
        c = self.c
        tam = f["tam"]
        fu = FUENTES["negra" if sec == 4 else "bold"](tam)
        lineas, alto = maquetar(f["palabras"], ANCHO_TEXTO, tam, fu)
        y0 = TEXTO_Y0 + (TEXTO_Y1 - TEXTO_Y0 - alto) / 2
        sale = suave((t - (f["t1"] - 0.14)) / 0.14) if f is not self.plan.frases[-1] else 0
        nombre = self.plan.secciones[sec]["nombre"]
        if nombre:
            x = MARGEN - 500 * (1 - suave((t - self.plan.secciones[sec]["t0"]) / 0.3))
            self.p.setColor(pal[2])
            c.drawString(nombre, x, TEXTO_Y0 - 28, FUENTES["bold"](44), self.p)
        for linea in lineas:
            for p, x, y, a in linea:
                k = (t - p["t0"]) / ENTRA_PALABRA
                if k <= 0:
                    continue
                e = rebote(k)
                alfa = min(1, k * 3) * (1 - sale)
                c.save()
                c.translate(MARGEN + x + a / 2, y0 + y + tam * 0.56 - sale * 60)
                c.rotate((1 - min(1, k)) * -9)
                c.scale(e, e)
                if p["dest"]:
                    self.p.setColor(pal[2])
                    self.p.setAlphaf(alfa)
                    pad = tam * 0.16
                    c.drawRoundRect(skia.Rect.MakeLTRB(-a / 2 - pad, -tam * 0.6, a / 2 + pad, tam * 0.52), 16, 16, self.p)
                    self.p.setColor(pal[0])
                else:
                    self.p.setColor(pal[1])
                self.p.setAlphaf(alfa)
                c.drawString(p["w"], -a / 2, tam * 0.3, fu, self.p)
                c.restore()
        self.p.setAlphaf(1)

    def confeti(self, pal, t, t0):
        c = self.c
        dt = t - t0
        for x, y, vx, vy, g, ci in self.chispas:
            py = y + vy * dt
            if py > ALTO:
                continue
            c.save()
            c.translate(x + vx * dt, py)
            c.rotate(g + dt * 240)
            self.p.setColor(pal[ci + 1])
            c.drawRect(skia.Rect.MakeXYWH(-13, -13, 26, 26), self.p)
            c.restore()

    def cuadro(self, t):
        sec, fr = self.plan.en(t)
        s = self.plan.secciones[sec]
        f = self.plan.frases[fr]
        pal = s["paleta"]
        self.fondo(sec, t)
        self.aura(pal, t)
        self.banda(pal, 70, t, 1)
        self.banda(pal, ALTO - 150, t, -1)
        self.ilustracion(f, pal, t)
        self.encabezado(pal)
        if sec == 4:
            self.confeti(pal, t, s["t0"])
        self.texto(f, pal, t, sec)
        if sec == len(self.plan.secciones) - 1:
            k = suave((t - (self.plan.duracion - 1.1)) / 0.3)
            if k > 0:
                self.p.setColor(pal[2])
                self.p.setAlphaf(k)
                self.c.drawString(self.cuenta, MARGEN, TEXTO_Y1 + 70, FUENTES["bold"](54), self.p)
                self.p.setAlphaf(1)
        return self.sup.toarray(colorType=skia.kRGBA_8888_ColorType)

    def imagen(self, t, ruta):
        self.cuadro(t)
        self.sup.makeImageSnapshot().save(str(ruta), skia.kPNG)


def video(plan, cuenta, salida):
    r = Render(plan, cuenta)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-crf", "21", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(salida),
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(round(plan.duracion * FPS)):
        p.stdin.write(r.cuadro(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg falló al dibujar el video")


def nota_marimba(frec, dur=0.7, vel=1.0):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 9)
    golpe = np.exp(-t * 80)
    s = (
        np.sin(2 * np.pi * frec * t) * env
        + 0.35 * np.sin(2 * np.pi * frec * 4 * t) * golpe
        + 0.14 * np.sin(2 * np.pi * frec * 10 * t) * golpe
    )
    return vel * s * (1 + 0.08 * np.sin(2 * np.pi * 11 * t))


def guardar_audio(x, salida):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-c:a", "aac", "-b:a", "160k", str(salida)],
        input=(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes(), check=True,
    )


def musica(indice, salida, duracion):
    """Marimba original en 3/4; cambia de melodía con cada palabra."""
    rng = np.random.default_rng(1000 + indice)
    tonica = 220 * 2 ** (rng.integers(-2, 4) / 12)
    pulso = 60 / 138
    acordes = [[0, 4, 7], [5, 9, 12], [7, 11, 14], [0, 4, 7]]
    largo = int(SR * (duracion + 2))
    izq, der = np.zeros(largo), np.zeros(largo)

    def poner(semi, tiempo, vel, pan):
        s = nota_marimba(tonica * 2 ** (semi / 12), vel=vel)
        i = int(tiempo * SR)
        if i >= largo:
            return
        s = s[: largo - i]
        izq[i : i + len(s)] += s * (1 - pan)
        der[i : i + len(s)] += s * pan

    compas, t = 0, 0.0
    while t < duracion:
        a = acordes[compas % 4]
        poner(a[0] - 12, t, 0.55, 0.35)
        for b in (1, 2):
            poner(a[1], t + b * pulso, 0.28, 0.45)
            poner(a[2], t + b * pulso, 0.28, 0.55)
        for k in range(6):
            if rng.random() < 0.8:
                poner(int(rng.choice(a)) + 12, t + k * pulso / 2, 0.5, 0.62)
        t += 3 * pulso
        compas += 1
    x = np.stack([izq, der], 1)[: int(SR * duracion)]
    fin = np.minimum(1, (len(x) - np.arange(len(x))) / (SR * 0.8))[:, None]
    guardar_audio(x * fin / np.max(np.abs(x)) * 0.8, salida)


def efectos(plan, salida):
    """Soplo en cada cambio de sección y un redoble de marimba en el remate."""
    largo = int(SR * (plan.duracion + 1))
    x = np.zeros(largo)
    rng = np.random.default_rng(plan.dia)
    n = int(SR * 0.42)
    soplo = np.convolve(rng.standard_normal(n), np.ones(9) / 9, "same") * np.sin(np.pi * np.arange(n) / n) ** 2
    for s in plan.secciones[1:]:
        i = int(s["t0"] * SR)
        x[i : i + n] += soplo
    t = plan.secciones[4]["t0"]
    for k, semi in enumerate((0, 4, 7, 12, 16, 19, 24)):
        s = nota_marimba(523.25 * 2 ** (semi / 12), 0.6, 0.7)
        i = int((t + k * 0.055) * SR)
        x[i : i + len(s)] += s
    guardar_audio(np.stack([x, x], 1) / max(1e-6, np.max(np.abs(x))) * 0.9, salida)


def narrar(segmentos, voz, carpeta):
    """Devuelve el audio de la narración y la duración de cada segmento."""
    from kokoro_onnx import Kokoro

    modelo = Path(os.environ.get("KOKORO_DIR", RAIZ / "modelo"))
    k = Kokoro(str(modelo / "kokoro-v1.0.onnx"), str(modelo / "voices-v1.0.bin"))
    pistas, tiempos = [], []
    sr = 24000
    for texto in segmentos:
        a, sr = k.create(texto, voice=voz, speed=1.08, lang="es")
        pistas += [a, np.zeros(int(PAUSA * sr), dtype=a.dtype)]
        tiempos.append(len(a) / sr + PAUSA)
    pcm = (np.clip(np.concatenate(pistas), -1, 1) * 32767).astype("<i2").tobytes()
    ruta = os.path.join(carpeta, "voz.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-", ruta],
        input=pcm, check=True,
    )
    return ruta, tiempos


def gancho(g):
    """Primera frase del video: tiene que nombrar la palabra en los primeros segundos."""
    return g.get("gancho") or f"¿Sabés de dónde viene la palabra {g['palabra']}?"


def preparar(indice):
    guiones = json.loads((RAIZ / "guiones.json").read_text(encoding="utf-8"))
    config = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    g = guiones[indice]
    cierre = f"Día {numero(indice + 1)}, de camino a un millón de seguidores. Seguime para la palabra de mañana."
    return g, config, [gancho(g), g["origen"], g["historia"], g["uso"], g["remate"], cierre]


def generar(indice, salida):
    g, config, segmentos = preparar(indice)
    salida = Path(salida)
    with tempfile.TemporaryDirectory() as tmp:
        voz, tiempos = narrar(segmentos, config.get("voz", "em_alex"), tmp)
        plan = Plan(g, indice + 1, tiempos)
        v, a, e, f = [os.path.join(tmp, n) for n in ("v.mp4", "a.m4a", "e.m4a", "f.mp4")]
        video(plan, config["cuenta"], v)
        musica(indice, a, plan.duracion)
        efectos(plan, e)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-i", voz, "-i", a, "-i", e, "-filter_complex",
             "[1:a]aresample=44100,loudnorm=I=-16:TP=-1.5,apad[n];[2:a]volume=0.13[m];[3:a]volume=0.32[e];"
             "[n][m][e]amix=inputs=3:duration=shortest:normalize=0[s]",
             "-map", "0:v", "-map", "[s]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", f],
            check=True,
        )
        salida.parent.mkdir(parents=True, exist_ok=True)
        os.replace(f, salida)
    pop = next((f["t0"] for f in plan.frases if f["ilu"] == "__pop__"), 0.0)
    return g, plan.duracion, int((pop + 0.6) * 1000)


def cuadros_prueba(indice, tiempos_ver, carpeta):
    """Dibuja fotogramas con tiempos de voz estimados, sin generar audio."""
    g, config, segmentos = preparar(indice)
    tiempos = [len(s) / 14.5 + PAUSA for s in segmentos]
    r = Render(Plan(g, indice + 1, tiempos), config["cuenta"])
    os.makedirs(carpeta, exist_ok=True)
    for t in tiempos_ver:
        r.imagen(t, f"{carpeta}/d{indice + 1:02d}_{t:05.1f}.png")
    return r.plan


if __name__ == "__main__":
    i = int(sys.argv[1])
    if len(sys.argv) > 3 and sys.argv[2] == "--cuadros":
        print(cuadros_prueba(i, [float(x) for x in sys.argv[3].split(",")], "../cuadros").duracion)
    else:
        print(generar(i, sys.argv[2] if len(sys.argv) > 2 else f"salida/dia-{i + 1:03d}.mp4")[1])
