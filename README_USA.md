# Estados Unidos · Blackboard y Modelos

El monitor `usa.html` incluye la pestaña **Blackboard** (alimentada desde `drive_ingestion/snapshots/usa.json` cuando se publica el libro maestro en la subcarpeta `USA` de Google Drive) y la pestaña **Modelos**.

En la sección Modelos, las tarjetas GDPNow y FRB/US abren sus vistas, con un botón para volver al menú. La página usa la última observación GDPNow disponible de la Fed de Atlanta. Es una tasa anualizada de crecimiento trimestral del PIB real y no es una previsión oficial del FOMC. El archivo gdpnow.json inicial es una instantánea verificada; la fecha figura en la pantalla.

update_gdpnow.py consulta la fuente oficial y valida trimestre, fecha y valor; si falla, conserva la última observación. El flujo de GitHub lo ejecuta junto con el resto de actualizaciones. El acceso directo desde GitHub Actions aún debe probarse. No exponga claves privadas en el repositorio.

FRB/US presenta ocho escenarios precalculados por el usuario en PyFRB/US para 2040T1–2045T4. Los gráficos permiten seleccionar escenarios y visualizar trayectorias o diferencias. Cambiar la selección no ejecuta el modelo. La trayectoria pública LONGBASE es ilustrativa y no es una previsión oficial de la Fed. Los shocks de consumo y vivienda afectan residuos de ecuaciones; el shock de tipos de cuatro trimestres se aplica repetidamente a la ecuación de política.

Para incorporar resultados nuevos, ejecute el modelo en un entorno compatible y desde esta carpeta use:

```
python actualizar_frbus.py /ruta/resultados.json
```

El actualizador valida la consistencia de la base y las diferencias y actualiza usa.html y frbus_resultados.json. Suba ambos archivos. GitHub Pages es estático: ejecutar PyFRB/US para un escenario arbitrario requiere un servicio de cálculo o una adaptación contrastada para navegador.
