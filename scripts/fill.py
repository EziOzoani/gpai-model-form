# scripts/fill.py
import json, sqlite3
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

DB = Path("data/model_docs.db")
DOCS = Path("docs/models")
TPL_DIR = Path("templates")

def fetch_models():
    cx = sqlite3.connect(DB)
    cur = cx.cursor()
    cur.execute("SELECT name, provider, region, size, release_date, data, completeness_percent, bonus_stars, label_x FROM models")
    out = []
    for name, provider, region, size, release, data, pct, stars, label in cur.fetchall():
        out.append({
            "model": {"model_name": name, "provider": provider, "region": region, "size": size, "release_date": release},
            "sections": json.loads(data or "{}"),
            "meta": {"label_x": label, "bonus_stars": stars, "completeness_percent": pct}
        })
    cx.close(); return out

if __name__ == "__main__":
    env = Environment(loader=FileSystemLoader(TPL_DIR))
    tpl = env.get_template("model_doc.md.j2")
    DOCS.mkdir(parents=True, exist_ok=True)
    for rec in fetch_models():
        context = {**rec["sections"], **{"model": rec["model"], "meta": rec["meta"]}}
        md = tpl.render(**context)
        slug = rec["model"]["model_name"].lower().replace(" ", "-")
        Path(DOCS, f"{slug}.md").write_text(md)