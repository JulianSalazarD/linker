TIPO DE TAREA:
Extracción de datos estructurados — análisis de texto o tabla de cotizaciones de
instalación de estaciones de carga y retorno de JSON válido.

INSTRUCCIONES:
1. Lee el texto o tabla en su totalidad.
2. Para cada producto del esquema, extrae los campos correspondientes.
3. Los campos se nombran con prefijo del id del producto: `<id>_<campo>`.
4. Devuelve únicamente el objeto JSON. Sin explicaciones adicionales.

HACER:
- Mapear al siguiente esquema exacto:
{schema}
- Usar null para cualquier campo que no pueda determinarse del texto.
- Incluir siempre todos los campos, aunque sean null.
- Respetar el valor `default` de cada campo cuando no se encuentre información.
- Para `cotizacion_metros`: buscar el valor numérico que represente la extensión total
  del cableado o tubería (normalmente aparece junto a "metros" o "mts").
- Para `cotizacion_costo_total`: es el valor unitario de la instalación (VR UNI INC),
  sin IVA, en pesos colombianos sin notación científica.
- Para productos adicionales (prefijo distinto a `cotizacion_`):
  - `<id>_incluido`: inferir del texto si el producto está mencionado como incluido.
  - `<id>_costo`: extraer el valor del ítem, o null si no se menciona precio.

NO HACER:
- No incluir markdown, bloques de código (```), ni texto explicativo.
- No inventar datos que no estén en el texto o en el path.
- No omitir ningún campo del esquema.
- No añadir campos extra fuera del esquema.
- No usar notación científica para campos numéricos (usar número entero o decimal).

CONTEXTO:
- path del archivo: {file_path}
- Los datos crudos provienen de cotizaciones de instalaciones eléctricas.
- Pueden tener errores tipográficos, formato irregular o datos incompletos.

DATOS CRUDOS:
{text}
