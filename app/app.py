"""
app.py – FastAPI + (ayrı modüldeki) Gradio arayüzü

UI kodu artık ui.py içindedir.
Bu dosya yalnızca:
  • /ask          – NL → SQL → sonuç
  • /save_view    – üretilen SQL’den CREATE VIEW
endpoint’lerini barındırır.
"""

import os, sys, json, re, threading, traceback, logging
from typing import List, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from sqlalchemy import text

# Proje yolunu ekle (models klasörü vb.)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from helper.api_helper import LLModel           # LLM + DB soyutlaması
from helper.interface_helper import QueryUI                          # → ayırdığımız yeni UI

# ─────────────────────────── API şemaları ──────────────────────────────
class QueryRequest(BaseModel):
    question: str
    set_id: int = 2          # 1=Factory, 2=Hammadde, 3=Hat

class QueryResponse(BaseModel):
    status: str              # success | error
    sql: Optional[str] = None
    rows: Optional[List[Dict]] = None
    gen_ms: Optional[float] = None
    exec_ms: Optional[float] = None
    error: Optional[str] = None

class SaveViewRequest(BaseModel):
    view_name: str
    set_id: int = 2

# ───────────────────────────── Ana sınıf ───────────────────────────────
log = logging.getLogger("app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

class Main:
    def __init__(self,
                 api_host: str = "127.0.0.1",
                 api_port: int = 8000,
                 ui_port: int = 7860):
        self.api_host, self.api_port, self.ui_port = api_host, api_port, ui_port
        self.models: Dict[int, LLModel] = {}
        self.last_sql: Dict[int, str] = {}

        # FastAPI
        self.app = FastAPI(title="Sorgu API", description="Serbest metin → SQL")
        self._register_routes()

    # ─────────── LLModel alma/oluşturma ───────────
    def _get_model(self, set_id: int) -> LLModel:
        if set_id not in self.models:
            self.models[set_id] = LLModel(table_set=set_id)
        return self.models[set_id]

    # ─────────── ENDPOINT’ler ───────────
    def _register_routes(self):

        @self.app.post("/ask", response_model=QueryResponse)
        async def ask(req: QueryRequest):
            log.info("► Soru alındı  set=%s  q=%s", req.set_id, req.question)
            try:
                rag = self._get_model(req.set_id)
                res = rag.answer(req.question)

                rows = res["rows"]
                if rows and not isinstance(rows[0], dict):
                    rows = [dict(enumerate(r)) for r in rows]

                # son SQL’i VIEW kaydetmek için sakla
                self.last_sql[req.set_id] = res["sql"]

                return QueryResponse(
                    status="success",
                    sql=res["sql"],
                    rows=rows,
                    gen_ms=res["gen_ms"],
                    exec_ms=res["exec_ms"],
                )
            except Exception as e:
                tb = traceback.format_exc()
                log.error("✗ Hata:\n%s", tb)
                return QueryResponse(status="error", error=str(e) + "\n" + tb)

        @self.app.post("/save_view")
        async def save_view(r: SaveViewRequest):
            sql = self.last_sql.get(r.set_id)
            if not sql:
                return {"status": "error", "msg": "Önce bir sorgu çalıştırın."}

            engine = self._get_model(r.set_id).engine
            safe = "".join(c for c in r.view_name if c.isalnum() or c == "_")
            clean_sql = re.sub(r'ORDER\\s+BY[\\s\\S]*?;?$', '', sql, flags=re.I).strip()
            stmt = f"CREATE OR ALTER VIEW [dbo].[{safe}] AS {clean_sql}"


            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
                return {"status": "success",
                        "msg": f"VIEW {safe} oluşturuldu / güncellendi"}
            except Exception as e:
                return {"status": "error", "msg": str(e)}

    # ─────────── Sunucuları başlat ───────────
    def run(self):
        # API sunucusu paralel thread’de
        def start_api():
            uvicorn.run(self.app, host=self.api_host, port=self.api_port,
                        log_level="warning")
        threading.Thread(target=start_api, daemon=True).start()

        # Gradio UI (ui.py)
        ui = QueryUI(api_host=self.api_host, api_port=self.api_port)
        ui.launch(server_name="127.0.0.1", server_port=self.ui_port)

# ─── main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Main().run()
