# Estados Unidos · Modelos

La página usa la última observación GDPNow disponible de la Fed de Atlanta. Es una tasa anualizada de crecimiento trimestral del PIB real y no es una previsión oficial del FOMC. El archivo gdpnow.json inicial es una instantánea verificada; la fecha figura en la pantalla.

update_gdpnow.py consulta la fuente oficial y valida trimestre, fecha y valor; si falla, conserva la última observación. El flujo de GitHub lo ejecuta junto con el resto de actualizaciones. El acceso directo desde GitHub Actions aún debe probarse. No exponga claves privadas en el repositorio.

El simulador de la Fed está pendiente de confirmar el modelo y de integrar y probar el motor. No calcula ni representa escenarios todavía. GitHub Pages es estático: ejecutar PyFRB/US para un escenario interactivo requiere un servicio de cálculo o una adaptación contrastada para navegador.
