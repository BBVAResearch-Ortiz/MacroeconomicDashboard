"""Regenerate the current complete dashboard from template.html and data.json."""
import json
import re
from pathlib import Path
tpl = Path("template.html").read_text(encoding="utf-8")
if tpl.count("__DATA__") != 1:
    raise ValueError("The template must contain exactly one __DATA__ placeholder")
data = json.loads(Path("data.json").read_text(encoding="utf-8"))
forecast = Path("forecasts.json")
if forecast.exists():
    data["forecasts"] = json.loads(forecast.read_text(encoding="utf-8"))
encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
bigdata_file = Path("bigdata.json")
bigdata = json.loads(bigdata_file.read_text(encoding="utf-8")) if bigdata_file.exists() else {"series": []}
big_encoded = json.dumps(bigdata, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = tpl.replace("__DATA__", encoded).replace("__BIGDATA__", big_encoded)
Path("espana.html").write_text(page, encoding="utf-8")
Path("artifact.html").write_text(page, encoding="utf-8")
turkey_data = json.dumps({"series": {}, "meta": {"refreshed": "", "n_series": 0}}, separators=(",", ":"))
turkey = tpl.replace("__DATA__", turkey_data).replace("__BIGDATA__", '{"series":[]}')
turkey = turkey.replace('<html lang="es">', '<html lang="es" data-monitor="turkey">', 1)
turkey = turkey.replace('<title>BBVA Research Monitor Macro España</title>',
                        '<title>BBVA Research Monitor Macro Turquía</title>', 1)
turkey = turkey.replace('<h1>BBVA Research Monitor Macro España</h1>',
                        '<h1>BBVA Research Monitor Macro Turquía</h1>', 1)
turkey = re.sub(r'<p class="lede">[^<]*</p>',
                '<p class="lede">Indicadores macroeconómicos y financieros de Turquía.</p>', turkey, count=1)
Path("turquia.html").write_text(turkey, encoding="utf-8")
print("espana.html, artifact.html and turquia.html regenerated")
