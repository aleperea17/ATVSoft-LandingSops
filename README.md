# SOPs Landing — Aumenta Tu Valor

Landing multi-paso (7 preguntas) → clave de acceso → popup con WhatsApp. Con atribución por slug de URL y panel de leads.

## Cómo funciona

1. La misma landing se sirve en cualquier URL: `tudominio.com/`, `tudominio.com/reel-marketing-01`, `tudominio.com/lo-que-sea` — el texto después de la barra (el **slug**) queda guardado junto con el lead, para saber por cuál video/SOP entró cada persona.
2. El visitante responde 7 preguntas (nombre, teléfono, email, Instagram, si gana dinero con contenido, si dirige/está asociado a una empresa de coaching, efectivo mensual recaudado).
3. Al terminar, se guarda el lead (`POST /api/leads`) y se pide la **clave de acceso**.
4. Las claves cargadas son **viral**, **hamburguesa**, **spotify** y **onboarding** (reutilizables, no distinguen mayúsculas/minúsculas). No se acepta ninguna otra. Si es válida, se abre el popup con el botón de WhatsApp (`https://wa.me/5491162626702`).

## Panel de leads

`tudominio.com/dashboard` — pide una clave de acceso al panel (**`sops-atv-2026`** por defecto, cambiarla en `app/main.py`, variable `DASHBOARD_PASSWORD`, antes de ir a producción).

Muestra una tabla con el total de leads por slug, y al hacer clic en una fila se ve el detalle (nombre, email, teléfono, Instagram, si usó la clave, fecha) de cada lead de ese slug.

## Cómo desplegar

```bash
# en el VPS, dentro de la carpeta del proyecto
docker compose up -d --build
docker compose logs backend --tail=30
```

Expone el puerto **8010** del host por defecto (`docker-compose.yml`) — ajustar si ese puerto ya está ocupado, y configurar Nginx + certbot para el dominio real.

Los datos se guardan en `backend/data/sops_landing.db` (SQLite), montado como volumen — no se pierden si se reconstruye el contenedor.

## Cómo cambiar las claves de acceso

Las claves viven en una sola lista, en `backend/app/database.py`:

```python
ACCESS_CODES = ("VIRAL", "HAMBURGUESA", "SPOTIFY", "ONBOARDING")
```

Se escriben en mayúsculas porque la validación normaliza a mayúsculas antes de comparar — el visitante puede escribir `viral`, `Viral` o `VIRAL`, todas entran.

Para agregar o sacar una clave: editar esa lista y reiniciar.

```bash
docker compose up -d --build
```

En cada arranque el backend sincroniza la tabla `codes` contra esa lista: da de alta las que falten y **desactiva cualquier otra** que haya quedado de antes. No borra nada — las viejas quedan con `active = 0`, así se conserva su `times_used` y se puede seguir viendo qué lead usó cuál.

Para ver el estado de las claves:

```bash
docker compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/sops_landing.db')
for row in conn.execute('SELECT code, active, times_used FROM codes'):
    print(row)
"
```

## Decisiones tomadas por defecto (revisar si hace falta cambiarlas)

- **Claves reutilizables, no de un solo uso** — cualquier cantidad de personas puede usar la misma palabra.
- **Password del panel hardcodeado** (`sops-atv-2026` en `app/main.py`) — cambiarlo antes de producción, ya que hoy es texto plano en el código.
- **Sin distinción de mayúsculas** en la clave de acceso (`viral` funciona igual que `VIRAL`).
- **La lista de claves manda sobre la base** — si alguien inserta un código a mano en la tabla `codes`, el próximo reinicio lo desactiva. La lista de `database.py` es la única fuente.
- **El slug es lo que esté después de la barra en la URL**, tal cual — no hay validación de que sea un slug "conocido"; cualquier texto ahí queda registrado como su propio slug nuevo automáticamente la primera vez que alguien complete el formulario con él.
