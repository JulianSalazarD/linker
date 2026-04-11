# Linker

CLI para generar informes y cotizaciones de instalaciones de cargadores de vehiculos electricos para PLUGUEA.

Pipeline: extraccion de archivo (DOCX/PDF) -> inferencia con LLM -> confirmacion en UI web -> generacion de documento.

## Requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (recomendado) o pip
- Tesseract OCR (para `--ocr`)
- LibreOffice (opcional, para conversion a PDF en Linux)

## Instalacion

```bash
# Clonar e instalar
git clone <repo-url>
cd linker
uv pip install .

# Verificar dependencias del sistema
linker install
```

El comando `linker install` detecta la plataforma y muestra instrucciones para instalar las dependencias faltantes (tesseract, libreoffice).

## Uso

```bash
# Generar informe desde un archivo
linker generate archivo.docx

# Con OCR y UI de confirmacion
linker generate archivo.pdf --ocr --confirm

# Elegir provider LLM (gemini, glm, minimax)
linker generate archivo.docx --provider gemini --confirm

# Generar tambien PDF
linker generate archivo.pdf --pdf

# Personalizar nombre y directorio de salida
linker generate archivo.pdf -n "MI INFORME" -d salida --pdf
```

### Subcomandos

| Comando | Descripcion |
|---|---|
| `linker generate` | Pipeline completo: extraccion -> LLM -> documento |
| `linker install` | Verificar dependencias del sistema |

### Opciones de `generate`

| Opcion | Corto | Descripcion |
|---|---|---|
| `--provider` | `-p` | Provider LLM: `gemini`, `glm`, `minimax` (default: `minimax`) |
| `--ocr` | `-o` | Usar OCR con Tesseract |
| `--confirm` | `-c` | Abrir UI de confirmacion en el navegador |
| `--port` | | Puerto para la UI (default: `8000`) |
| `--output-name` | `-n` | Nombre del documento de salida |
| `--output-dir` | `-d` | Directorio de salida (default: `pruebas`) |
| `--pdf` | | Generar tambien PDF |
| `--libreoffice` | `-l` | Usar LibreOffice para PDF |

## Estructura del proyecto

```
linker/
  main.py            # CLI y pipeline principal
  config/            # Templates, prompts, imagenes y configuracion
  processor/         # Extraccion de contenido (DOCX, PDF, OCR)
  llm_client/        # Clientes LLM (Gemini, GLM, MiniMax)
  products/          # Logica de productos y cotizaciones
  generator/         # Generacion de documentos DOCX
  confirmer/         # UI web (FastAPI) para confirmar datos
  tests/             # Tests
```

## Configuracion

Crear un archivo `.env` en la raiz con las API keys necesarias segun el provider:

```env
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
ZHIPU_API_KEY=...
MINIMAX_API_KEY=...
```

## Licencia

[MIT](LICENSE)
