TIPO DE TAREA:
Extracción de datos estructurados — análisis de texto crudo de cotizaciones
de servicios de transporte y retorno de JSON válido.

INSTRUCCIONES:
1. Lee el texto crudo en su totalidad.
2. Extrae cada campo del esquema JSON definido abajo.
3. Para el campo `direccion`, extrae EXCLUSIVAMENTE el fragmento del
   nombre de archivo hasta el primer guión bajo (_).
   Ejemplo: si path = "/docs/Cr 30 # 20-45_240101_120000.docx",
   entonces direccion = "Cr 30 # 20-45".
4. Devuelve únicamente el objeto JSON. Sin explicaciones adicionales.

HACER:
- Mapear al siguiente esquema exacto:
{schema}
- Usar null para cualquier campo que no pueda determinarse del texto.
- Incluir siempre todos los campos, aunque sean null.
- Respetar el valor `default` de cada campo cuando no se encuentre información.

NO HACER:
- No incluir markdown, bloques de código (```), ni texto explicativo.
- No inventar datos que no estén en el texto o en el path.
- No omitir ningún campo del esquema.
- No añadir campos extra fuera del esquema.
- No usar notación científica para campos numéricos (usar número entero o decimal).

CONTEXTO:
- path del archivo: {file_path}
- Los datos crudos provienen de cotizaciones (posiblemente OCR o texto libre).
- Pueden tener errores tipográficos, formato irregular o datos incompletos.

DATOS CRUDOS:
{text}
