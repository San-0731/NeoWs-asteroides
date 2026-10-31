# Consulta de Asteroides Cercanos a la Tierra

Aplicación de consola en Python que consulta los asteroides que se acercan a la Tierra en un rango de fechas usando la API **NeoWs** de NASA, y los muestra como registros en consola y en tres gráficas. Guarda las respuestas en un caché local y permite exportar los resultados a CSV.

> Proyecto personal e independiente. No está afiliado ni respaldado por NASA.

## Características

- Consulta por rango de fechas (máximo 7 días, el límite del endpoint *Feed* de NeoWs).
- Tres gráficas: cantidad de objetos por día, distancia de aproximación vs tamaño, y objetos catalogados como peligrosos vs no peligrosos.
- Caché en disco: no repite peticiones que ya hizo.
- Exportación de los resultados a CSV, evitando duplicados por la pareja fecha del asteroide + nombre.
- Validación de fechas, manejo de errores de red y aviso específico cuando NASA limita las solicitudes (HTTP 429).
- Clave de NASA leída, en orden, desde los ajustes del usuario, `NASA_API_KEY` o `DEMO_KEY`.
- Pruebas unitarias para API, caché, fechas, gráficas, procesamiento y exportación.

## Requisitos

- Probado con **Python 3.14** en **Ubuntu 26.04 LTS**.
- Conexión a internet para las consultas nuevas.
- En Ubuntu, dos paquetes del sistema:
  - `python3-venv`, para crear el entorno virtual.
  - `python3-tk`, para que se abran las ventanas de las gráficas.

```bash
sudo apt update
sudo apt install python3-venv python3-tk
```

## Instalación

```bash
git clone https://github.com/San-0731/NeoWs-asteroides.git

cd NeoWs-asteroides

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

El entorno virtual hay que activarlo (`source venv/bin/activate`) cada vez que abras una terminal nueva para usar el programa.

## Configurar la API key

La aplicación busca la clave en este orden:

1. `NASA_API_KEY` en `settings.json`, dentro de la carpeta de datos del usuario.
2. La variable de entorno `NASA_API_KEY` (también se puede definir en un `.env` en la raíz del proyecto).
3. `DEMO_KEY`, si no encuentra una clave en los pasos anteriores.

Al iniciar, la aplicación crea `settings.json` con una clave vacía si todavía no existe. Puedes agregar manualmente tu clave con este formato:

```json
{
  "NASA_API_KEY": "tu_clave_aqui"
}
```

La pantalla para editar los ajustes desde la aplicación aún no está implementada. También puedes crear un `.env` en la raíz del proyecto:

```env
NASA_API_KEY=tu_clave_aqui
```

El `.env` está en `.gitignore`; no compartas ni subas claves reales al repositorio.

Si no hay una clave configurada, se usa `DEMO_KEY`, que tiene límites bajos: [30 peticiones por hora y 50 al día por dirección IP](https://api.nasa.gov/assets/html/authentication.html). NASA puede responder HTTP 429 cuando se alcanza el límite; la aplicación muestra un aviso en español y recomienda esperar o configurar una clave propia. Una clave registrada permite 1.000 peticiones por hora. Las consultas servidas desde caché no hacen una petición nueva.

## Uso

```bash
python Neows.py
```

El programa muestra un menú de 5 opciones:

| Opción | Qué hace |
|---|---|
| 1. Realizar petición a la API de NASA | Pide las fechas y consulta NeoWs, o usa el caché si ya tiene esa consulta. |
| 2. Construir datos y mostrar resultados | Procesa la respuesta e imprime un registro por asteroide. |
| 3. Construir gráficos | Abre un submenú para elegir y mostrar una de las tres gráficas. |
| 4. Guardar resultados a CSV | Agrega los resultados al archivo CSV en la carpeta de datos del usuario. |
| 5. Salir | Cierra el programa. |

**El orden importa:** las opciones 3 y 4 necesitan haber ejecutado antes la 1 y la 2.

### Ubicación de los datos

El caché, el CSV y los ajustes se guardan en la carpeta de datos del usuario que determina `platformdirs`, usando el autor `San-0731` y el nombre de aplicación `NeoWs-Asteroides`. La ruta depende del sistema operativo y ya no está dentro de la carpeta del proyecto. En Linux normalmente es `~/.local/share/San-0731/NeoWs-Asteroides/`; en Windows y macOS se utiliza la ubicación de datos de usuario correspondiente a cada plataforma.

Al iniciar, la aplicación crea la carpeta y, si falta, `settings.json` con `NASA_API_KEY` vacío. En esa ubicación también se guardan `cache_neows.json` y `Historial_Consultas.csv`.

### Fechas

- Formato `AAAA-MM-DD`, por ejemplo `2026-08-01`.
- Si dejas la fecha final vacía (Enter), se consulta solo la fecha inicial.
- La fecha final no puede ser anterior a la inicial.
- Si el rango supera los 7 días, se recorta automáticamente a 7 días desde la fecha inicial.

### Ejemplo de un registro

```json
{
    "Fecha": "2026-08-06",
    "Name": "136770 (1996 PC1)",
    "Estimated_Diameter_(Km)": 0.459240286,
    "Threat_Level": false,
    "Close_Approach_Distance_(km)": 61668127.54939708,
    "Close_Approach_Velocity_(km/h)": 83073.9012659539
}
```

| Campo | Significado |
|---|---|
| `Fecha` | Fecha de la aproximación más cercana a la Tierra. |
| `Name` | Designación del objeto según NASA/JPL. |
| `Estimated_Diameter_(Km)` | Diámetro máximo estimado, en kilómetros. Es una estimación. |
| `Threat_Level` | Si NASA lo cataloga como "potencialmente peligroso" (`is_potentially_hazardous_asteroid`). Es una clasificación por tamaño y órbita; no significa que vaya a impactar. |
| `Close_Approach_Distance_(km)` | Distancia a la Tierra en su aproximación, en kilómetros. |
| `Close_Approach_Velocity_(km/h)` | Velocidad relativa en la aproximación, en km/h. |

Si un dato no viene en la respuesta de la API, el campo queda en `null` y ese registro se omite solo de la gráfica que lo necesita.

## Cómo funciona el caché

Las respuestas se guardan en `cache_neows.json`, dentro de la carpeta de datos del usuario, con el rango de fechas exacto como clave. Si repites un rango vigente que ya consultaste, el programa lo carga del caché sin pedirlo otra vez a la API y sin necesidad de internet.

La caducidad se calcula usando tiempos en UTC y depende de la fecha final del rango:

- **Permanente:** si la consulta se guardó después de la fecha final del rango (un rango ya terminado).
- **12 horas:** si la consulta se guardó antes de que terminara el rango, es decir, rangos que llegan a hoy o al futuro. NASA puede agregar objetos nuevos o corregir órbitas, así que esos datos se renuevan.
- **Cada rango es independiente:** `2026-08-01 – 2026-08-07` y `2026-08-01 – 2026-08-05` son consultas distintas y cada una hace su propia petición.

## Estructura del proyecto

```
.
├── Neows.py                  # Punto de entrada: menú de consola y flujo principal
├── neo_app/
│   ├── api.py                # Petición a NeoWs y lectura de la API key
│   ├── cache.py              # Caché en JSON con caducidad y guardado seguro
│   ├── config.py             # Rutas de datos del usuario
│   ├── fechas.py             # Solicitud y validación de fechas
│   ├── procesamiento.py      # Convierte la respuesta de la API en registros
│   ├── graficas.py           # Las tres gráficas (matplotlib)
│   └── exportacion.py        # Exportación a CSV
├── tests/
│   ├── test_api.py
│   ├── test_cache.py
│   └── test_neows.py
├── requirements.txt
└── .gitignore
```

## Pruebas

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python -m unittest discover -s tests
```

Las pruebas no usan internet ni modifican tu caché ni tu CSV.

## Limitaciones conocidas

- Solo usa el endpoint *Feed* de NeoWs (consulta por fechas). No usa *Lookup* ni *Browse*.
- El CSV evita filas duplicadas según la pareja fecha del asteroide + nombre. Si falta alguno de esos dos datos, conserva la fila porque no puede determinar con seguridad si es duplicada.
- Es una aplicación de consola. Hay que tener Python instalado para usarla.
- Solo se ha probado en Ubuntu.

## Próximos pasos

- [ ] Interfaz gráfica.
- [ ] Versión portable, para usarla sin instalar Python ni las dependencias.
- [ ] Pantalla de ajustes para editar la API key sin modificar manualmente `settings.json` ni `.env`.
- [ ] README en inglés.

## Créditos

Datos de la API **NeoWs** (Near Earth Object Web Service) de NASA, disponible en [api.nasa.gov](https://api.nasa.gov/).