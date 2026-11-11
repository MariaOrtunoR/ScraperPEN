
Plan de trabajo para completar el scraper del Portal Estadístico del Notariado

## Estado al 08/11/2026

La fase de preparación de SQLite está completada: `log_descargas` existe, las conexiones Python activan las claves foráneas y `datos_crudos` contiene sólo las 2.088 observaciones históricas válidas. Se retiraron los 3.564 registros no válidos tras crear la copia `inmobiliario_backup_antes_migracion_validez_20261108_102632.db`. No se han fabricado registros de log históricos, porque la clasificación anterior no acredita una consulta concreta al portal.

El scraper ya usa rutas relativas a la raíz, variables de entorno para las credenciales y el catálogo SQLite. Su modo predeterminado sigue siendo una prueba con `29710`; `PEN_EJECUTAR_TODOS_CP=1` habilitará el catálogo completo únicamente tras validarla. Resta comprobar en el portal los selectores y el mensaje exacto de datos provinciales.
Vamos a seguir un orden progresivo: primero corregiremos la base de datos y el código, después haremos una prueba controlada con un único código postal y, cuando hayamos validado todo, ejecutaremos la descarga completa de los códigos postales de Málaga.

Hay una decisión de diseño que ya hemos acordado y que aplicaremos en todos los pasos: el log conservará el resultado de cada consulta, mientras que datos_crudos contendrá únicamente datos válidos y se actualizará cuando volvamos a descargar un periodo existente.
Fase 1. Revisar y preparar la base de datos
1.1. Revisar el esquema actual de SQLite

- Comprobar las tablas existentes y sus columnas.
- Verificar la relación entre codigos_postales y datos_crudos.
- Comprobar las claves primarias, foráneas y restricciones de unicidad.
- Revisar los registros actuales para no perder información.
  1.2. Crear la tabla log_descargas

Propuesta de estructura:
Campo	Descripción
id	Identificador único
fecha_descarga	Fecha y hora de la consulta
cp	Código postal consultado
estado	Resultado de la consulta
valido	1 si los datos son propios del CP; 0 si son provinciales; NULL si hubo error técnico
observaciones	Mensaje del portal o descripción del error

Los estados permitirán distinguir, como mínimo:

- completada: consulta realizada correctamente.
- sin_datos_cp: el portal muestra datos provinciales en sustitución de los del CP.
- error: fallo técnico durante la consulta o descarga.
  1.3. Revisar datos_crudos
- Mantener la clave única (cp, periodo, metrica).
- Guardar exclusivamente datos válidos.
- Mantener la actualización de registros existentes mediante UPSERT.
- Comprobar que los códigos postales existen en codigos_postales antes de insertar.
- Activar las claves foráneas en cada conexión SQLite.
- Revisar si debemos retirar la columna valido de datos_crudos, puesto que la validez quedará registrada en log_descargas.
  1.4. Proteger la información existente
- Crear una copia de seguridad de la base de datos.
- No borrar los datos históricos existentes.
- Revisar cómo tratar los registros que anteriormente se marcaron como no válidos mediante la lista estática de CP. No debemos asumir que esa clasificación histórica equivale a haber detectado el mensaje del portal.
  Fase 2. Corregir DatabaseManager.py
  2.1. Adaptar las funciones de conexión
- Activar PRAGMA foreign_keys = ON.
- Comprobar que las tablas tienen el esquema esperado.
- Evitar que el programa cree accidentalmente tablas incompletas.
  2.2. Incorporar las operaciones del log
- Crear la función para registrar cada consulta.
- Guardar el CP, la fecha, el estado, la validez y las observaciones.
- Registrar también los errores técnicos.
  2.3. Adaptar el almacenamiento de datos
- Si el CP es válido, guardar las tres métricas.
- Si el CP no es válido, no insertar datos en datos_crudos.
- Si el periodo ya existe, actualizar su valor.
- Si el periodo no existe, insertar un registro nuevo.
  2.4. Comprobar las operaciones
- Verificar que no se duplican registros.
- Verificar que no se insertan CP inexistentes.
- Verificar que una actualización no deja datos obsoletos.
  Fase 3. Corregir ScraperPEN.py
  3.1. Seguridad y configuración
- Retirar las credenciales del código fuente.
- Leer usuario y contraseña desde variables de entorno o un archivo .env.
- Evitar que las credenciales se publiquen en Git.
  3.2. Corregir las rutas
- Utilizar rutas relativas a la raíz del proyecto, no al directorio desde el que se ejecuta el programa.
- Guardar los PDF en data/raw/descargas_pdf/.
- Guardar los Excel en data/raw/descargas_excel/.
  3.3. Corregir la selección de códigos postales
- Leer el catálogo de CodigosPostalesMalaga.xlsx o de la tabla codigos_postales.
- Eliminar la asignación que sobrescribe la lista principal con ["29710"].
- Mantener el CP 29710 únicamente como código de prueba.
- Comprobar que se procesan todos los códigos postales del catálogo, sin duplicados.
  3.4. Mejorar la navegación
- Comprobar que el inicio de sesión se ha realizado correctamente.
- Verificar que el CP se ha seleccionado correctamente.
- Esperar a que terminen de cargar las estadísticas.
- Controlar los errores de navegación y los tiempos de espera.
- Evitar que un fallo en un CP detenga todo el proceso.
  3.5. Detectar la validez de los datos

Este es uno de los cambios más importantes.

Después de pulsar «Más estadísticas» y antes de descargar el PDF:

- Buscar el mensaje HTML que indica que los datos no corresponden a la ubicación indicada y que se muestran los datos de la provincia de Málaga.
- Si aparece, registrar sin_datos_cp y valido = 0.
- No descargar ni guardar las métricas provinciales como si fueran datos del CP.
- Si no aparece, registrar completada y valido = 1, y continuar con la descarga.
  Si se produce un error técnico, registrar error y valido = NULL.

3.6. Descargar y procesar las métricas

Para los CP válidos:

- Descargar el PDF.
- Extraer las tres métricas: precio_m2, compraventas e importe_medio.
- Generar el Excel correspondiente.
- Guardar los datos en SQLite.
- Comprobar que las tres métricas se han extraído correctamente.
  Fase 4. Prueba controlada con el CP 29710
  Ejecutaremos el scraper únicamente para el código postal 29710.

Comprobaremos:

1. Que inicia sesión correctamente.
2. Que selecciona el CP correcto.
3. Que llega a «Más estadísticas».
4. Que detecta correctamente el mensaje de datos provinciales, si aparece.
5. Que registra el resultado en log_descargas.
6. Que descarga el PDF cuando corresponde.
7. Que genera el Excel con las tres métricas.
8. Que almacena los datos en SQLite únicamente si son válidos.
   También comprobaremos qué sucede si ejecutamos dos veces la descarga: no deben aparecer duplicados en datos_crudos, pero sí dos entradas independientes en log_descargas.
   Fase 5. Validación de resultados
   Antes de ampliar la ejecución, revisaremos:

Archivos

- Que los PDF se han descargado correctamente.
- Que los Excel contienen las tres métricas.
- Que los nombres de archivo identifican correctamente el CP y la fecha.
  Base de datos
- Que cada consulta tiene su correspondiente entrada en log_descargas.
- Que los CP no válidos no tienen datos provinciales insertados en datos_crudos por esa consulta.
- Que los CP válidos tienen sus registros.
- Que los valores se actualizan correctamente cuando se repiten periodos.
- Que no existen duplicados ni errores de integridad referencial.
  Pruebas adicionales
- Un CP válido.
- Un CP que provoque el mensaje de datos provinciales.
- Un error técnico simulado, para comprobar que queda registrado correctamente.
  Si el 29710 resulta válido, esta prueba nos servirá para comprobar el camino de éxito. Para probar las otras dos situaciones necesitaremos CP o condiciones que permitan reproducirlas.
  Fase 6. Descarga completa de Málaga
  Una vez superadas las pruebas:

1. Activar el catálogo completo de códigos postales.
2. Ejecutar el scraper para los 160 CP.
3. Registrar individualmente cada resultado en log_descargas.
4. Descargar y almacenar únicamente los datos válidos.
5. Actualizar los periodos ya existentes.
6. Revisar el resumen final de la ejecución.
   El resultado será una base de datos que permita consultar tanto los datos inmobiliarios disponibles como la evolución de la disponibilidad de información de cada código postal.

Resumen del orden de ejecución

1. Preparar SQLite

   Copia de seguridad, revisión del esquema y creación de log_descargas.
2. Corregir DatabaseManager.py

   Log de consultas, claves foráneas y actualización de datos válidos.
3. Corregir ScraperPEN.py

   Credenciales, rutas, catálogo completo, navegación y detección del mensaje provincial.
4. Prueba con 29710

   Verificar el proceso completo de principio a fin.
5. Validar resultados

   Revisar archivos, métricas, log y SQLite.
6. Descarga completa

   Procesar los 160 códigos postales de Málaga.
   Cómo lo abordaría
   Mi recomendación es que trabajemos fase por fase y archivo por archivo, sin reescribir todo de golpe. Primero revisamos el esquema real de la base de datos y preparamos una copia de seguridad. Después modificamos DatabaseManager.py, lo probamos de forma independiente y solo entonces pasamos al scraper.

Así evitaremos que un problema de navegación, de almacenamiento o de estructura de SQLite se mezcle con los demás.

Este será nuestro plan de trabajo de referencia.
