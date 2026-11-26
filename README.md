# Monitor Macro España

Dashboard estático para GitHub Pages. Incluye Pizarra de series, euríbor diario y conexiones directas al BCE, Comisión Europea, OCDE, INE y Banco de España. También mantiene series publicadas por BDSICE, incluidos los indicadores sintéticos del propio Ministerio de Economía.

La actualización se ejecuta mediante `.github/workflows/update-data.yml`. Las instrucciones sobre las fuentes, la validación y las series pendientes están en [README_FUENTES_ORIGINALES.md](README_FUENTES_ORIGINALES.md). La información del euríbor está en [README_EURIBOR.md](README_EURIBOR.md).

Antes de subir este paquete, compara su contenido con la rama actual de GitHub para conservar los cambios posteriores. Las descargas automáticas deben verificarse ejecutando el workflow en GitHub.

## Pruebas del dashboard

GitHub Actions ejecuta las pruebas en cada pull request y cada push a `main`. Las pruebas de navegador usan los datos del repositorio y comprueban la navegación, el idioma, las modalidades de Blackboard, el ajuste estacional y las descargas CSV.

```sh
node --test
python -m pip install playwright==1.65.2
python -m playwright install chromium --only-shell
python -B -m unittest discover -s tests -v
```
