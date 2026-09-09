# SOPs Landing — Aumenta Tu Valor

Landing multi-paso (7 preguntas) → clave de acceso → popup con WhatsApp. Con atribución por slug de URL y panel de leads.

## Cómo funciona

1. La misma landing se sirve en cualquier URL: `tudominio.com/`, `tudominio.com/reel-marketing-01`, `tudominio.com/lo-que-sea` — el texto después de la barra (el **slug**) queda guardado junto con el lead, para saber por cuál video/SOP entró cada persona.
2. El visitante responde 7 preguntas (nombre, teléfono, email, Instagram, si gana dinero con contenido, si dirige/está asociado a una empresa de coaching, efectivo mensual recaudado).
3. Al terminar, se guarda el lead (`POST /api/leads`) y se pide la **clave de acceso**.
4. La clave real cargada es **ATV-5051** (reutilizable, no distingue mayúsculas/minúsculas). Si es válida, se abre el popup con el botón de WhatsApp (`https://wa.me/5491162626702`).

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

## Cómo agregar o desactivar códigos de acceso

Por ahora es por línea de comandos (no hay pantalla para esto):

```bash
# Ver todos los códigos
docker compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/sops_landing.db')
for row in conn.execute('SELECT code, active, times_used FROM codes'):
    print(row)
"

# Agregar un código nuevo
docker compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/sops_landing.db')
conn.execute(\"INSERT INTO codes (code, active) VALUES ('NUEVOCODIGO', 1)\")
conn.commit()
"

# Desactivar un código (sin borrarlo)
docker compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/sops_landing.db')
conn.execute(\"UPDATE codes SET active = 0 WHERE code = 'ATV-5051'\")
conn.commit()
"
```

## Decisiones tomadas por defecto (revisar si hace falta cambiarlas)

- **Clave reutilizable, no de un solo uso** — cualquier cantidad de personas puede usar `ATV-5051`.
- **Password del panel hardcodeado** (`sops-atv-2026` en `app/main.py`) — cambiarlo antes de producción, ya que hoy es texto plano en el código.
- **Sin distinción de mayúsculas** en la clave de acceso (`atv-5051` funciona igual que `ATV-5051`).
- **El slug es lo que esté después de la barra en la URL**, tal cual — no hay validación de que sea un slug "conocido"; cualquier texto ahí queda registrado como su propio slug nuevo automáticamente la primera vez que alguien complete el formulario con él.
