# ⚡ Toolbox Pro v1.2 — Sistema Maestro de Herramientas

Aplicación de escritorio en **Python 3.11+**, **PySide6** y **QML (Qt Quick Controls 2)** diseñada para analistas de operaciones de datos (*Data Operations Analysts*). Automatiza tareas de oficina con archivos **Excel (`.xlsx`, `.xls`, `.xlsm`)**, **CSV/TSV** y consultas a **Oracle Database** en modo *thin*.

---

## 🛠️ Herramientas Incluidas

### Sección: Preparar
1. **📊 Conversión CSV (`csv_converter`)**:
   - Detección automática de codificación (`utf-8-sig`, `utf-8`, `cp1252`, `latin-1`) y delimitador (`,`, `;`, `\t`, `|`), conservando acentos, la letra `ñ` y ceros a la izquierda en códigos/SKUs.
   - Conversión individual o **por lotes** (varios archivos a la vez) hacia `.xlsx` con formato corporativo o `.csv`.
2. **🧹 Limpieza de datos (`data_cleaner`)**:
   - 6 reglas combinables por columna o sobre todo el archivo: quitar espacios sobrantes, normalizar mayúsculas/minúsculas/título, eliminar filas duplicadas, unificar formatos de fecha (`AAAA-MM-DD`, `DD/MM/AAAA`, etc.), reemplazar vacíos (tratando `"NULL"`, `"N/A"`, `"-"` como vacíos) y limpiar caracteres no imprimibles/acentos.
   - Vista previa **"Antes ⇒ Después"** con conteo de celdas y filas afectadas por cada regla antes de guardar.
   - Guardado y carga de perfiles de limpieza en JSON (`perfiles_limpieza.json`).
3. **🗂️ Detector de duplicados (`duplicate_finder`)**:
   - Detección de fila completa o por combinación de columnas elegidas, ignorando opcionalmente mayúsculas y espacios.
   - Genera salida separada sin tocar el archivo original: **Sin Duplicados**, **Solo Duplicados** (con `GRUPO_DUPLICADO` y `NUM_REPETICIONES`) y **Resumen**.

### Sección: Analizar
4. **🔍 Perfilado de archivo (`file_profiler`)**:
   - Se ejecuta automáticamente en segundo plano al cargar el archivo.
   - Muestra filas, columnas, tamaño en disco y diagnóstico por columna: tipo detectado (`texto`, `entero`, `decimal`, `fecha`, `booleano`, `mixto`), `% de nulos/vacíos`, valores únicos, mínimo/máximo, rango de longitud de texto y Top 3 valores más frecuentes.
   - Alertas visuales automáticas (columnas con muchos nulos, valor constante único, tipos mixtos, filas duplicadas).
5. **⚖️ Comparar archivos — Diff (`file_diff`)**:
   - Compara Archivo A (Original) vs Archivo B (Nuevo) por una o varias columnas clave.
   - Reporta filas **NUEVAS**, **ELIMINADAS**, **MODIFICADAS** (con detalle exacto celda por celda: `Clave | Columna | Valor Anterior | Valor Nuevo`) e **IGUALES**.
   - Opciones de tolerancia numérica, ignorar mayúsculas/espacios y validación de claves duplicadas. En Excel resalta automáticamente las celdas modificadas.
6. **🔗 Cruzar archivos — Merge / VLOOKUP (`file_merge`)**:
   - Cruce relacional (`left`, `inner`, `right`, `outer`) y filtro rápido de **"Ver solo registros sin coincidencia"** (solo izquierdo, solo derecho o ambos).
   - Emparejamiento manual de una o varias columnas clave (aunque tengan distinto nombre entre archivos) y selección de columnas del archivo derecho a traer.
   - Alerta automática cuando claves duplicadas en el archivo derecho multiplican filas (**relación 1:N**).

### Sección: Datos Externos
7. **🗄️ Oracle SQL (`oracle_sql`)**:
   - Conexión `python-oracledb` en **modo thin** (no requiere instalar Oracle Instant Client) con apertura y cierre garantizados mediante *context managers* y descarga por lotes (`fetchmany`).
   - Detección automática de parámetros nombrados (`:fecha_inicio`, `:codigo`) generando controles dinámicos por tipo (`texto`, `numero`, `fecha` con selector de fecha) enviados **exclusivamente como variables bind** (sin concatenación SQL).
   - Modo **Solo Lectura** que advierte y pide confirmación si detecta `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER` o `MERGE`.
   - Gestor de **Consultas Favoritas** (`favoritas.json`) con búsqueda, edición, duplicación, eliminación y sugerencia de últimos valores usados por parámetro.

---

## 🔐 Configuración (`.env` y Seguridad)

Las credenciales de Oracle viven **exclusivamente** en un archivo `.env` en la raíz del proyecto. Nunca se incluyen en el código fuente, en QML, en `favoritas.json` ni en los logs.

1. Copia la plantilla incluida en el repositorio:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Abre el archivo `.env` y completa tus datos reales:
   ```ini
   ORACLE_USER=tu_usuario
   ORACLE_PASSWORD=tu_contraseña
   ORACLE_HOST=servidor-oracle.empresa.local
   ORACLE_PORT=1521
   ORACLE_SERVICE_NAME=ORCLPDB1
   # Opcional (tiene prioridad sobre HOST/PORT/SERVICE_NAME):
   ORACLE_DSN=
   ```
3. **Importante**: **NUNCA** subas el archivo `.env` a Git o GitHub. El archivo `.gitignore` ya está configurado para excluir `.env`, `.env.*` (excepto `.env.example`), los resultados de salida (`salidas/`), logs y archivos de trabajo (`.xlsx`, `.csv`).
4. Si el archivo `.env` no existe o le faltan variables, la aplicación **no se detiene**: la pestaña **Oracle SQL** mostrará qué variables faltan configurar (solo sus nombres), mientras todas las demás herramientas de Excel y CSV funcionan con total normalidad.

---

## 🚀 Instalación y Ejecución

1. Instala las dependencias desde `requirements.txt`:
   ```powershell
   pip install -r requirements.txt
   ```
2. Inicia la aplicación:
   ```powershell
   python main.py
   ```

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias y de integración con `pytest` (usando datos de ejemplo en `tests/data/` y dobles/mocks para Oracle sin requerir conexión real):

```powershell
pytest -v
```

