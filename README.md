# Habla chapín

Publica un Reel narrado cada día sobre el origen de las palabras de Guate.

- `guiones.json`: guiones listos. Se publican en orden.
- `banco-palabras.json`: palabras pendientes de investigar.
- `publicados.json`: palabras ya publicadas.
- `config.json`: nombre de la cuenta y hashtags.
- `generar.py`: narra, anima el video y compone la marimba.
- `ilustraciones.py`: ilustraciones animadas, dibujadas con código.

- `publicar.py`: publica en Instagram.
- `tiktok.py`: sube el video del día a la bandeja de TikTok como borrador.

Secreto del repositorio: `IG_TOKEN`. `GH_PAT` es opcional: solo hace falta si el token de Instagram caduca y hay que renovarlo.
Las fuentes Archivo Black y Poppins tienen licencia SIL Open Font.

TikTok (borradores): secretos `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` y `GH_PAT`.
Para conectar: guardá el código de autorización como `TIKTOK_CODE` y corré el flujo
manualmente con «Conectar TikTok» activado. Eso crea `TIKTOK_REFRESH_TOKEN`.
