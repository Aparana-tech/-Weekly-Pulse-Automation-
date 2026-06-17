from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

app = FastAPI(title="Pulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"

@app.get("/api/products")
def get_products():
    """Get all configured products."""
    try:
        with open(CONFIG_DIR / "products.json", "r") as f:
            return json.load(f).get("products", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/runs")
def get_runs():
    """Get all runs from the ledger."""
    try:
        ledger_path = PROJECT_ROOT / ".pulse_ledger.json"
        if not ledger_path.exists():
            return []
        with open(ledger_path, "r") as f:
            runs = json.load(f)
            
        # Inject doc_id from products.json
        products_path = CONFIG_DIR / "products.json"
        if products_path.exists():
            with open(products_path, "r") as f:
                products_config = json.load(f)
                products_list = products_config.get("products", [])
                
                for run in runs:
                    for product in products_list:
                        if product.get("slug") == run.get("product"):
                            run["doc_id"] = product.get("doc_id")
                            break
                            
                    # Inject preview from report JSON
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
                            
        return runs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/{run_id}")
def get_report(run_id: str):
    """Get the PulseReport JSON for a specific run."""
    # The run_id might not exactly match the filename. We reconstruct filename.
    # We parse the run_id from the ledger to get the filename if needed, or
    # the client passes `product_year_week`
    
    # We'll assume the client passes the file prefix like `groww_2026_W25`
    report_path = DOWNLOADS_DIR / f"{run_id}_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found at {report_path.name}")
        
    try:
        with open(report_path, "r") as f:
            report_data = json.load(f)
            
        # Read the products config to get the doc_id
        products_path = CONFIG_DIR / "products.json"
        if products_path.exists():
            with open(products_path, "r") as f:
                products_config = json.load(f)
                parts = run_id.split("_")
                if len(parts) >= 1:
                    product_slug = parts[0]
                    for product in products_config.get("products", []):
                        if product.get("slug") == product_slug:
                            doc_id = product.get("doc_id")
                            if doc_id:
                                report_data["doc_id"] = doc_id
                            break
                            
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
