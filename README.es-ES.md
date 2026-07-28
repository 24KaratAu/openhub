# OpenHub

Un centro de descubrimiento y gestor de paquetes con interfaz de usuario de terminal (TUI) y enfoque en el teclado para herramientas, habilidades y agentes de codificación con IA.

Construido con Python, Textual y SQLite — sin necesidad de configuración inicial.

---

## Requisitos y Soporte de Plataforma

* **Python**: 3.10+
* **Sistemas Operativos**: Linux, macOS, Windows (PowerShell / Windows Terminal)

---

## Ecosistema y Compatibilidad con Agentes de IA

OpenHub exporta herramientas utilizando el **Universal Open Agent Skills Standard** (`SKILL.md`), lo que hace que las herramientas exportadas sean utilizables instantáneamente en los asistentes de codificación e IDEs de IA modernos:

| Herramienta de IA / IDE de Agente | Soportado | Ruta de Integración de Exportación |
| :--- | :---: | :--- |
| **OpenCode** | Sí | `./.opencode/skills/` & `~/.config/opencode/` |
| **Claude Code / Desktop** | Sí | `./.agents/skills/` & `~/.agents/skills/` |
| **Cursor Editor** | Sí | `./.agents/skills/` |
| **Windsurf / Cascade** | Sí | `./.agents/skills/` |
| **Roo Code / Cline** | Sí | `./.agents/skills/` |
| **AutoGen / CrewAI** | Sí | Formato estándar `SKILL.md` |

---

## Inicio Rápido

### Instalar vía pipx (Recomendado)
```bash
pipx install git+https://github.com/24KaratAu/openhub.git
openhub
```

### Instalar vía pip
```bash
pip install git+https://github.com/24KaratAu/openhub.git
openhub
```

### Desarrollo Local
```bash
git clone https://github.com/24KaratAu/openhub.git
cd openhub
pip install -e .
openhub
```

---

## Características y Arquitectura

1. **Catálogo Centrado en el Dashboard**: Muestra paneles de catálogo analizables con repositorios en tendencia, lanzamientos recientes, utilidades de rápido crecimiento y joyas ocultas.
2. **Búsqueda Difusa Basada en Intenciones**: Al presionar `/` o `S` se abre un menú desplegable de comandos estilo Spotlight. La coincidencia tolerante a errores se ejecuta localmente usando `rapidfuzz` a través de nombres, descripciones, temas y casos de uso.
3. **Colecciones Curadas**: Explore flujos de trabajo seleccionados como "AI Engineer Starter Pack", "Claude Desktop Servers", "Cursor Editor Skills" o "Python Toolkit".
4. **Tarjetas de Metadatos Analizables**: Los elementos del repositorio se renderizan con calificaciones de calidad visuales (`★★★★★`), etiquetas de lenguaje y niveles de dificultad.
5. **Arranque Instantáneo y Sincronización en Segundo Plano**: Arranca instantáneamente (< 100ms) desde la caché local de SQLite mientras los datos frescos de GitHub se sincronizan silenciosamente en hilos de fondo.
6. **Exportación Universal de Habilidades**: Presione `E` para exportar instrucciones de prompt `SKILL.md` con un solo clic directamente a `./.agents/skills/` y `./.opencode/skills/`.
7. **Log de Historial de Actividad**: Registra todas las acciones (Instalado, Exportado, Fallido, Eliminado) en una base de datos local SQLite persistente.

---

## Documentación Técnica y Heurísticas

OpenHub se basa en algoritmos deterministas en lugar de métricas subjetivas para calificar la calidad, clasificar los niveles de dificultad y curar las secciones.

Lea la documentación técnica completa en [`HOW_IT_WORKS.md`](file:///home/au24/Documents/opencode-project/HOW_IT_WORKS.md).

---

## Atajos de Teclado

| Atajo | Acción |
| :--- | :--- |
| **`H`** | Navegar al Dashboard de Inicio |
| **`B`** | Explorar por Casos de Uso |
| **`C`** | Explorar Colecciones Curadas |
| **`S`** / **`/`** | Alternar paleta de Búsqueda Spotlight |
| **`I`** | Ver paquetes Instalados |
| **`E`** | Exportar Habilidad directamente (`SKILL.md` y definición de Agente) |
| **`L`** | Ver logs del Historial de Operaciones |
| **`R`** | Refrescar caché y sincronizar repositorios |
| **`F`** | Ciclar filtros de tipo de implementación (en modo Explorar) |
| **`Enter`** | Mostrar Detalles / Instalar repositorio seleccionado |
| **`Esc`** | Salir de detalles / Cancelar modal / Cerrar Búsqueda |
| **`Q`** | Salir de la aplicación |

---

## Estructura del Código Base

```
openhub/
│
├── README.md               # Guía de inicio rápido, requisitos del sistema y documentación
├── HOW_IT_WORKS.md          # Documentación del motor técnico y puntuación
├── pyproject.toml          # Configuración del paquete y punto de entrada de la CLI de openhub
├── install.sh              # Script instalador de shell
├── run.py                  # Script ejecutor independiente
├── requirements.txt        # Dependencias del paquete (textual, httpx, rapidfuzz)
├── .github/
│   └── workflows/
│       ├── ci.yml          # Flujo de trabajo de pruebas automatizadas en PRs
│       └── release.yml     # Flujo de trabajo de lanzamiento automatizado de GitHub
│
└── app/
    ├── __init__.py
    ├── main.py             # Orquestador principal de la aplicación y bucle de trabajador de fondo
    ├── cache.py            # Gestor de conexión de base de datos SQLite
    ├── client.py           # Cliente de API de GitHub y almacenamiento en caché
    ├── classifier.py       # Clasificación heurística y algoritmos de Puntuación de Calidad
    ├── exporter.py         # Exportador universal de SKILL.md y Agentes
    ├── installer.py        # Subproceso ejecutor de instalación asíncrona
    │
    ├── screens/            # Vistas de pantalla de la UI
    │   ├── home.py         # Vista del Dashboard de Inicio
    │   ├── browse.py       # Vista de lista de exploración por casos de uso
    │   ├── collections.py  # Vista de Listas Curadas
    │   ├── search.py       # Vista de menú desplegable superpuesta de Spotlight
    │   ├── details.py      # Vista previa de readme en Markdown y superposiciones de confirmación de Instalación
    │   └── history.py      # Vista del log de actividad de operaciones
    │
    └── widgets.py          # Elementos personalizados de diseño de tarjeta analizable
```
