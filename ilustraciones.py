"""Ilustraciones animadas, dibujadas con código. Son originales y no usan archivos.

Cada función dibuja alrededor de (0, 0), en un cuadro de unos 560 px de ancho,
y recibe t: segundos desde que apareció en pantalla.
"""
import math
from math import cos, pi, sin

import skia

BORDE = 0xFF22130A
CREMA = 0xFFFFF6E5
ORO = 0xFFFFC233
VERDE = 0xFF2E9E5B
ROJO = 0xFFD8342B
CAFE = 0xFF8A5A33
CAFE2 = 0xFFC48A52
CELESTE = 0xFF4FB3E8
GRIS = 0xFF8D99A6
_ANCHO = 11


def color(c):
    return skia.Color4f.FromColor(c)


class L:
    """Lápiz: figuras rellenas con borde grueso, estilo calcomanía."""

    def __init__(self, canvas):
        self.c = canvas
        self.rel = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style)
        self.bor = skia.Paint(
            AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=_ANCHO,
            StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap, Color=BORDE,
        )

    def _pinta(self, dibujar, c, borde):
        self.rel.setColor(c)
        dibujar(self.rel)
        if borde:
            dibujar(self.bor)

    def circulo(self, x, y, r, c, borde=True):
        self._pinta(lambda p: self.c.drawCircle(x, y, r, p), c, borde)

    def elipse(self, x, y, rx, ry, c, borde=True):
        self._pinta(lambda p: self.c.drawOval(skia.Rect.MakeLTRB(x - rx, y - ry, x + rx, y + ry), p), c, borde)

    def caja(self, x0, y0, x1, y1, r, c, borde=True):
        self._pinta(lambda p: self.c.drawRoundRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), r, r, p), c, borde)

    def poli(self, pts, c, borde=True, cerrar=True):
        ruta = skia.Path()
        ruta.addPoly([skia.Point(*q) for q in pts], cerrar)
        if cerrar:
            self._pinta(lambda p: self.c.drawPath(ruta, p), c, borde)
        else:
            self.bor.setColor(c)
            self.c.drawPath(ruta, self.bor)
            self.bor.setColor(BORDE)

    def linea(self, pts, c=BORDE, ancho=None):
        ruta = skia.Path()
        ruta.addPoly([skia.Point(*q) for q in pts], False)
        prev = self.bor.getStrokeWidth()
        if ancho:
            self.bor.setStrokeWidth(ancho)
        self.bor.setColor(c)
        self.c.drawPath(ruta, self.bor)
        self.bor.setColor(BORDE)
        self.bor.setStrokeWidth(prev)

    def texto(self, s, x, y, fuente, c):
        self.rel.setColor(c)
        self.c.drawString(s, x - fuente.measureText(s) / 2, y, fuente, self.rel)

    def gira(self, x, y, grados):
        self.c.save()
        self.c.translate(x, y)
        self.c.rotate(grados)

    def fin(self):
        self.c.restore()


def mortero(l, t, pal, f):
    golpe = abs(sin(t * 5))
    y = -210 + 130 * golpe
    l.gira(70, y, 18 + 8 * golpe)
    l.caja(-30, -190, 30, 110, 28, CAFE2)
    l.circulo(0, 118, 46, CAFE2)
    l.fin()
    if golpe < 0.3:
        for i in range(7):
            a = -pi * (i + 0.5) / 7
            d = 150 + 200 * (0.3 - golpe)
            l.circulo(cos(a) * d, -40 + sin(a) * d * 0.6, 14, pal[2], False)
    l.poli([(-215, -50), (215, -50), (150, 190), (-150, 190)], pal[3])
    l.caja(-245, -80, 245, -30, 25, CAFE2)
    l.caja(-120, 185, 120, 225, 16, CAFE)


def copa(l, t, pal, f):
    a = sin(t * 2.4) * 9
    l.gira(0, 40, a)
    l.poli([(-120, -210), (120, -210), (70, 150), (-70, 150)], CREMA)
    n = -100 + 12 * sin(t * 6)
    l.poli([(-104 + 6, n), (104 - 6, n + 16 * sin(t * 5)), (70, 145), (-70, 145)], ORO, False)
    for i in range(5):
        y = 130 - ((t * 120 + i * 62) % 210)
        l.circulo(-40 + i * 20, y, 8, CREMA, False)
    l.poli([(-120, -210), (120, -210), (70, 150), (-70, 150)], 0x00000000)
    l.caja(-90, 150, 90, 190, 14, CREMA)
    l.fin()


def moneda(l, t, pal, f):
    x = cos(t * 5)
    y = -18 * abs(sin(t * 5))
    ancho = max(30, abs(x) * 210)
    l.elipse(0, 215, 150 + 40 * abs(x), 18, 0x33000000, False)
    l.elipse(0, y, ancho, 210, ORO)
    l.elipse(0, y, ancho * 0.76, 160, 0xFFF4A81D)
    if abs(x) > 0.35:
        l.c.save()
        l.c.translate(0, y)
        l.c.scale(abs(x), 1)
        l.texto("Q", 0, 78, f["negra"](220), BORDE)
        l.c.restore()


def billetes(l, t, pal, f):
    for i in range(7):
        x = -240 + (i * 83) % 480 + 34 * sin(t * 3 + i)
        y = -280 + ((t * 230 + i * 170) % 490)
        l.gira(x, y, 26 * sin(t * 3.4 + i * 2))
        l.caja(-100, -52, 100, 52, 10, VERDE)
        l.circulo(0, 0, 30, CREMA)
        l.texto("Q", 0, 18, f["negra"](46), BORDE)
        l.fin()


def cartera(l, t, pal, f):
    l.gira(0, 80, 2.5 * sin(t * 4))
    l.caja(-235, -120, 235, 150, 32, CAFE)
    l.caja(-235, -120, 235, -40, 32, CAFE2)
    l.caja(120, -10, 260, 70, 30, CAFE2)
    l.circulo(200, 30, 15, ORO)
    l.fin()
    x, y = 70 * sin(t * 2.3), -170 - ((t * 60) % 150) + 18 * sin(t * 7)
    aleteo = 18 + 44 * abs(sin(t * 18))
    l.elipse(x - aleteo * 0.8, y, aleteo, 34, CREMA)
    l.elipse(x + aleteo * 0.8, y, aleteo, 34, CREMA)
    l.elipse(x, y, 12, 28, BORDE, False)


def zapato(l, t, pal, f):
    golpe = abs(sin(t * 4.2))
    y = -150 * golpe + 60
    if golpe < 0.25:
        l.texto("CHAP!", 170, -160, f["negra"](84), pal[2])
    l.elipse(0, 245, 250 - 80 * golpe, 18, 0x33000000, False)
    l.gira(0, y, -6 * golpe)
    l.poli([(-230, 30), (-200, -130), (-120, -130), (-60, -40), (160, 10), (225, 70), (225, 110), (-230, 110)], pal[3])
    l.caja(-235, 105, 235, 215, 18, CAFE2)
    l.caja(-200, -145, -100, -115, 14, ORO)
    l.linea([(-40, -8), (-10, 40)], CREMA, 12)
    l.linea([(25, 8), (50, 50)], CREMA, 12)
    l.fin()


def barco(l, t, pal, f):
    y = 18 * sin(t * 2.2)
    l.gira(0, y, 4 * sin(t * 1.8))
    l.linea([(0, 80), (0, -240)], BORDE, 16)
    l.poli([(12, -225), (180, -30), (12, -20)], CREMA)
    l.poli([(-12, -205), (-150, -40), (-12, -30)], CREMA)
    l.poli([(-235, 60), (235, 60), (165, 165), (-165, 165)], CAFE)
    l.caja(-235, 45, 235, 80, 12, CAFE2)
    l.fin()
    for fila, (yb, c) in enumerate(((160, CELESTE), (205, 0xFF2D86C4))):
        pts = [(x, yb + 15 * sin(x / 55 + t * 3 + fila * 2)) for x in range(-280, 281, 16)]
        l.poli(pts + [(280, 245), (-280, 245)], c)


def bandera(l, t, pal, f):
    l.caja(-262, -250, -238, 260, 10, CAFE2)
    columnas = 36
    ancho = 480 / columnas
    for i in range(columnas):
        x = -238 + i * ancho
        o = 18 * sin(i / 4.5 - t * 5) * (i / columnas)
        c = CREMA if columnas / 3 <= i < 2 * columnas / 3 else CELESTE
        l.rel.setColor(c)
        l.c.drawRect(skia.Rect.MakeLTRB(x, -220 + o, x + ancho + 1, 80 + o), l.rel)


def hotdog(l, t, pal, f):
    s = 1 + 0.06 * sin(t * 7)
    l.c.save()
    l.c.translate(0, 20 * sin(t * 3.5))
    l.c.rotate(-10 + 4 * sin(t * 2.5))
    l.c.scale(s, 2 - s)
    l.caja(-260, 10, 260, 125, 56, 0xFFE9B566)
    l.caja(-290, -55, 290, 60, 56, 0xFFC7492B)
    l.linea([(-235 + i * 7, -34 + 11 * sin(i / 4 + t * 4)) for i in range(68)], 0xFF8CC63F, 40)
    l.linea([(-235 + i * 7, -12 + 17 * sin(i / 2.4 + t * 5)) for i in range(68)], ORO, 17)
    l.caja(-260, -125, 260, -38, 44, 0xFFF0C680)
    l.fin_escala()


def pizarra(l, t, pal, f):
    l.caja(-270, -190, 270, 150, 14, 0xFF1F5C4A)
    l.caja(-285, -205, 285, -180, 8, CAFE2)
    l.caja(-285, 140, 285, 165, 8, CAFE2)
    palabra = "¡SHUCOS!"[: 1 + int(t * 7) % 12]
    l.texto(palabra, 0, 10, f["negra"](84), CREMA)
    n = min(1, t / 1.2)
    l.linea([(-180 + 360 * n * i / 12, 50 + 12 * sin(i * 1.4)) for i in range(13)], ORO, 9)
    l.caja(180 + 20 * sin(t * 9), 95, 240 + 20 * sin(t * 9), 125, 7, CREMA)


def libro(l, t, pal, f):
    l.poli([(0, -130), (-250, -170), (-250, 160), (0, 200)], CREMA)
    l.poli([(0, -130), (250, -170), (250, 160), (0, 200)], CREMA)
    fase = (t * 1.1) % 1
    x = 250 * cos(pi * fase)
    l.poli([(0, -130), (x, -170 + 40 * sin(pi * fase)), (x, 160 - 25 * sin(pi * fase)), (0, 200)], ORO)
    for i in range(4):
        y = -80 + i * 58
        l.linea([(-205, y - 8), (-60, y + 13)], GRIS, 10)
        if fase < 0.45:
            l.linea([(65, y + 13), (205, y - 8)], GRIS, 10)


def lupa(l, t, pal, f):
    l.texto("?", 0, 125, f["negra"](370), pal[1])
    x, y = 110 * sin(t * 2.2), -50 + 80 * sin(t * 3.1)
    l.gira(x, y, 40)
    l.caja(-26, 125, 26, 305, 22, CAFE2)
    l.fin()
    l.circulo(x, y, 138, 0x66FFFFFF)
    l.circulo(x, y, 138, 0x00000000)
    l.linea([(x - 78, y - 44), (x - 40, y - 86)], CREMA, 13)


def sandalia(l, t, pal, f):
    l.gira(0, 25 * sin(t * 3), 18 + 16 * sin(t * 3.4))
    l.caja(-125, -255, 125, 255, 115, CAFE)
    l.caja(-92, -220, 92, 220, 88, CAFE2, False)
    l.linea([(-125, -55), (125, -55)], pal[3], 44)
    l.linea([(-125, 45), (125, 45)], pal[3], 44)
    l.linea([(0, -205), (0, -60)], pal[3], 24)
    l.fin()


def chumpa(l, t, pal, f):
    a = 7 * sin(t * 4.3)
    y = 16 * sin(t * 2.2)
    l.gira(-168, -125 + y, 12 + a)
    l.poli([(-30, -10), (40, 30), (-40, 330), (-125, 305)], pal[3])
    l.fin()
    l.gira(168, -125 + y, -12 - a)
    l.poli([(30, -10), (-40, 30), (40, 330), (125, 305)], pal[3])
    l.fin()
    l.poli([(-160, -190 + y), (160, -190 + y), (178, 195 + y), (-178, 195 + y)], pal[3])
    l.caja(-178, 165 + y, 178, 230 + y, 18, pal[2])
    l.poli([(-85, -205 + y), (0, -115 + y), (85, -205 + y)], CREMA)
    l.linea([(0, -115 + y), (0, 225 + y)], ORO, 13)
    l.caja(-125, 40 + y, -55, 120 + y, 8, pal[2])
    l.caja(55, 40 + y, 125, 120 + y, 8, pal[2])


def avion(l, t, pal, f):
    fase = (t * 0.45) % 1
    x, y = -340 + 680 * fase, 90 - 170 * fase + 75 * sin(fase * 2 * pi * 1.5)
    rastro = []
    for i in range(1, 18):
        q = fase - i * 0.035
        if q > 0:
            rastro.append((-340 + 680 * q, 90 - 170 * q + 75 * sin(q * 2 * pi * 1.5)))
    for i, q in enumerate(rastro):
        if i % 2 == 0:
            l.circulo(q[0], q[1], 9, CREMA, False)
    l.gira(x, y, -14 + 22 * cos(fase * 2 * pi * 1.5))
    l.poli([(155, 0), (-120, -112), (-65, 0)], CREMA)
    l.poli([(155, 0), (-65, 0), (-110, 86)], 0xFFD9D2C3)
    l.fin()


def pato(l, t, pal, f, escala=1):
    for i in range(7):
        x = 300 - ((t * 240 + i * 100) % 600)
        l.linea([(x, 225), (x + 50, 225)], BORDE, 9)
    bal = 11 * sin(t * 8)
    for lado in (-1, 1):
        p = 34 * sin(t * 8 + (pi if lado > 0 else 0))
        l.linea([(lado * 44, 120), (lado * 44 + p, 200)], 0xFFF28C28, 22)
        l.elipse(lado * 44 + p + 22, 208, 44, 14, 0xFFF28C28)
    l.gira(0, 25 * abs(sin(t * 8)) - 10, bal)
    l.elipse(-10, 40, 190, 130, CREMA)
    l.poli([(-185, 25), (-262, -50), (-160, -35)], CREMA)
    l.circulo(115, -125, 88, CREMA)
    l.elipse(216, -112, 56, 25, 0xFFF28C28)
    l.circulo(140, -148, 13, BORDE, False)
    l.gira(-25, 25, 12 * sin(t * 8) - 8)
    l.elipse(-25, 25, 100, 58, 0xFFE8DCC4)
    l.fin()
    l.fin()


def arbol(l, t, pal, f):
    a = 3.6 * sin(t * 1.9)
    for i in range(7):
        y = -135 + ((t * 85 + i * 83) % 355)
        x = -240 + i * 80 + 32 * sin(t * 2 + i)
        l.elipse(x, y, 18, 10, ORO, False)
    l.poli([(-48, 240), (48, 240), (28, -30), (-28, -30)], CAFE)
    l.gira(0, 0, a)
    for x, y, r in ((-120, -105, 118), (112, -105, 118), (0, -190, 132), (0, -55, 128)):
        l.circulo(x, y, r, ORO)
    for x, y, r in ((-120, -105, 118), (112, -105, 118), (0, -190, 132), (0, -55, 128)):
        l.circulo(x, y, r - 12, ORO, False)
    l.fin()


def tinte(l, t, pal, f):
    l.gira(0, 0, 28 * sin(t * 2.1) + 4)
    l.caja(-125, -135, 125, 215, 40, pal[3])
    l.caja(-50, -210, 50, -128, 12, CREMA)
    l.caja(-95, -35, 95, 110, 14, CREMA)
    l.texto("RUBIO", 0, 62, f["negra"](46), BORDE)
    l.fin()
    for i in range(4):
        y = -235 + ((t * 300 + i * 105) % 420)
        l.circulo(195 + 15 * sin(i), y, 19, ORO)


def chucho(l, t, pal, f):
    cola = 26 * sin(t * 14)
    l.gira(-225, -30, cola - 45)
    l.caja(-16, -125, 16, 12, 14, CAFE2)
    l.fin()
    for x in (-175, -85, 65, 155):
        p = 16 * sin(t * 6 + x)
        l.caja(x - 25 + p, 55, x + 25 + p, 200, 18, CAFE2)
    l.caja(-235, -75, 195, 105, 88, CAFE2)
    y = 8 * sin(t * 4)
    l.circulo(165, -120 + y, 98, CAFE2)
    l.elipse(240, -90 + y, 60, 38, 0xFFE5C49B)
    l.circulo(286, -103 + y, 15, BORDE, False)
    l.gira(105, -180 + y, 14 * sin(t * 7) - 12)
    l.elipse(-5, 55, 38, 88, CAFE)
    l.fin()
    l.circulo(185, -142 + y, 12, BORDE, False)
    l.elipse(235, -38 + y, 20, 34 + 6 * sin(t * 12), ROJO)
    l.caja(-235, 15, -110, 40, 8, CAFE, False)


def _culebra(l, t, pal, dy, fase, largo=30, c=None):
    c = c if c is not None else pal[3]
    pts = []
    for i in range(largo):
        x = -255 + i * (510 / largo)
        pts.append((x, dy + 48 * sin(i / 3.2 + t * 5 + fase)))
    for x, y in pts:
        l.circulo(x, y, 34, BORDE, False)
    for i, (x, y) in enumerate(pts):
        l.circulo(x, y, 28, ORO if i % 6 == 2 else c, False)
    x, y = pts[-1]
    l.elipse(x + 28, y, 62, 44, c)
    l.circulo(x + 40, y - 13, 9, BORDE, False)
    if sin(t * 8 + fase) > 0:
        l.linea([(x + 86, y), (x + 142, y + 8)], ROJO, 8)


def serpiente(l, t, pal, f):
    _culebra(l, t, pal, 0, 0)


def mellizas(l, t, pal, f):
    _culebra(l, t, pal, -100, 0, 28)
    _culebra(l, t, pal, 115, 0, 28, 0xFF2E9E5B)


def pavo(l, t, pal, f):
    abre = 1 + 0.09 * sin(t * 4.5)
    colores = (ROJO, ORO, 0xFF2E9E5B, 0xFFF28C28)
    for i in range(11):
        a = (-158 + i * 13.6) * abre
        l.gira(-35, 65, a + 90)
        l.caja(-38, -295, 38, 0, 36, colores[i % 4])
        l.fin()
    l.elipse(-25, 85, 150, 128, CAFE)
    for x in (-65, 15):
        l.linea([(x, 195), (x, 248)], 0xFFF28C28, 18)
    y = 25 * sin(t * 6)
    l.linea([(55, 15), (112, -90 + y)], CAFE, 62)
    l.circulo(120, -115 + y, 56, 0xFFD97B5E)
    l.circulo(136, -128 + y, 11, BORDE, False)
    l.poli([(172, -112 + y), (225, -90 + y), (172, -80 + y)], ORO)
    l.elipse(155, -55 + y + 6 * sin(t * 9), 19, 48, ROJO)


def _fin_escala(self):
    self.c.restore()


L.fin_escala = _fin_escala

PROPS = {
    n: g
    for n, g in globals().items()
    if callable(g) and not n.startswith("_") and n not in ("L", "color", "cos", "sin", "skia")
}
