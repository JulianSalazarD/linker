TIPO DE TAREA:
Extracción de datos estructurados — análisis de texto o tabla de cotizaciones de
instalación de estaciones de carga y retorno de JSON válido.

INSTRUCCIONES:
1. Lee el texto o tabla en su totalidad.
2. Extrae cada campo del esquema JSON definido abajo.
3. Devuelve únicamente el objeto JSON. Sin explicaciones adicionales.

HACER:
- Mapear al siguiente esquema exacto:
{schema}
- Usar null para cualquier campo que no pueda determinarse del texto.
- Incluir siempre todos los campos, aunque sean null.
- Respetar el valor `default` de cada campo cuando no se encuentre información.
- Para `metros`: buscar el valor numérico que represente la extensión total
  del cableado o tubería (normalmente aparece junto a "metros" o "mts").
- Para `costo_total`: es el valor unitario de la instalación (VR UNI INC),
  sin IVA, en pesos colombianos sin notación científica.
- Para `tiene_wallbox`: inferir del texto si se menciona wallbox como incluido.
- Para `costo_wallbox`: extraer el valor del ítem wallbox, o null si no se
  menciona precio. Si no se encuentra, usar null.
- Para `tiene_nema_14_50`: inferir si se menciona adaptador NEMA 14-50.
- Para `costo_nema_14_50`: extraer el valor del adaptador NEMA 14-50, o null
  si no se menciona precio. Si no se encuentra, usar null.

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
