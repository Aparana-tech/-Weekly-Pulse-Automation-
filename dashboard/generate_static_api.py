import json
import os
from pathlib import Path

def generate():
    PROJECT_ROOT = Path(__file__).parent.parent
    CONFIG_DIR = PROJECT_ROOT / "config"
    DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
    PUBLIC_API_DIR = Path(__file__).parent / "public" / "api"
    PUBLIC_REPORTS_DIR = PUBLIC_API_DIR / "reports"
    
    os.makedirs(PUBLIC_REPORTS_DIR, exist_ok=True)
    
    # 1. Generate runs.json
    runs = []
    ledger_path = PROJECT_ROOT / ".pulse_ledger.json"
    if ledger_path.exists():
        with open(ledger_path, "r") as f:
            runs = json.load(f)
            
    products_path = CONFIG_DIR / "products.json"
    products_list = []
    if products_path.exists():
        with open(products_path, "r") as f:
            products_list = json.load(f).get("products", [])
            
    for run in runs:
        for product in products_list:
            if product.get("slug") == run.get("product"):
                run["doc_id"] = product.get("doc_id")
                break
                
        report_path = DOWNLOADS_DIR / f"{run.get('product')}_{run.get('iso_year')}_W{run.get('iso_week'):02d}_report.json"
        if report_path.exists():
            try:
                with open(report_path, "r") as rf:
                    report_data = json.load(rf)
                    themes = report_data.get("themes", [])
                    if themes:
                        top_theme = themes[0]
                        run["preview"] = {
                            "theme_name": top_theme.get("name"),
                            "quote": top_theme.get("quotes", [{}])[0].get("text") if top_theme.get("quotes") else None,
                            "action": top_theme.get("actions", [{}])[0].get("title") if top_theme.get("actions") else None
                        }
            except Exception:
                pass
                
    with open(PUBLIC_API_DIR / "runs.json", "w") as f:
        json.dump(runs, f)
        
    # 2. Generate individual report JSONs
    for report_file in DOWNLOADS_DIR.glob("*_report.json"):
        with open(report_file, "r") as f:
            report_data = json.load(f)
            
        parts = report_file.name.split("_")
        if len(parts) >= 1:
            product_slug = parts[0]
            for product in products_list:
                if product.get("slug") == product_slug:
                    report_data["doc_id"] = product.get("doc_id")
                    break
                    
        run_id = report_file.name.replace("_report.json", "")
        with open(PUBLIC_REPORTS_DIR / f"{run_id}.json", "w") as f:
            json.dump(report_data, f)
            
    print("Static API generated successfully in dashboard/public/api/")

if __name__ == "__main__":
    generate()
