import gradio as gr
import pandas as pd
import requests
from typing import List, Dict, Any

__all__ = ["QueryUI"]

# ───────────────────────── Tema Tanımı ────────────────────────────
# Gradio 4.x: Soft teması üzerine mavi tonlar
BLUE_THEME = gr.themes.Soft(
    primary_hue="blue",      # ana vurgu rengi
    neutral_hue="slate",     # ikincil / nötr gri ton
)

# İsteğe bağlı minik CSS eklemesi (arka plan ve sohbet balonları)
CSS_OVERRIDES = """
/* Uygulama arka planı hafif açık mavi */
body {background-color:#f0f8ff;}
/* Chatbot balon renkleri */
.chatbot .message.user{background:#1e3a8a!important;color:#fff;}
.chatbot .message.assistant{background:#2563eb!important;color:#fff;}
"""


class QueryUI:
    """Gradio tabanlı arayüz – Chat & VIEW oluşturma sekmeleri (Mavi tema)"""

    def __init__(self, *, api_host: str = "127.0.0.1", api_port: int = 8000):
        self.api_host = api_host
        self.api_port = api_port

    # ───────────────────────── Yardımcı Fonksiyonlar ──────────────────────────
    @staticmethod
    def _rows_to_md(rows: List[Dict[str, Any]], max_rows: int = 100) -> str:
        if not rows:
            return "(sonuç yok)"
        df = pd.DataFrame(rows).head(max_rows)
        return df.to_markdown(index=False)

    def _post(self, path: str, payload: Dict[str, Any], *, timeout: int = 120):
        url = f"http://{self.api_host}:{self.api_port}{path}"
        return requests.post(url, json=payload, timeout=timeout)

    # ───────────────────────── Event Handler'lar ──────────────────────────
    def _talk(self, history: List, question: str, set_id: int, sql_code_md, table_df):
        """Sohbet düğmesine basıldığında çalışır"""
        question = question.strip()
        if not question:
            return history, "", sql_code_md

        try:
            resp = self._post("/ask", {"question": question, "set_id": set_id})
            if resp.status_code != 200:
                history.append((question, f"❌ Sunucu HTTP {resp.status_code}: {resp.text[:300]}"))
                return history, "", sql_code_md

            data = resp.json()
            if data.get("status") != "success":
                history.append((question, f"❌ Hata: {data.get('error', 'Bilinmeyen hata')}"))
                return history, "", sql_code_md

            # Başarılı
            sql = data["sql"]
            rows = data.get("rows", [])
            df = pd.DataFrame(rows) 
            table_md = self._rows_to_md(rows)
            answer = (
                f"**SQL:**\n```sql\n{sql}\n```\n\n" +
                f"**Sonuç (ilk satırlar):**\n{table_md}\n\n" +
                f"_LLM {data.get('gen_ms', '?')} ms | SQL {data.get('exec_ms', '?')} ms_"
            )
            history.append((question, answer))
            sql_code_md = gr.update(value=f"```sql\n{sql}\n```", visible=True)
            
            table_df = gr.update(value=df, visible=True, interactive=False)
            return history, "", sql_code_md, table_df
        except Exception as e:
            history.append((question, f"❌ İstemci hatası: {e}"))
            return history, "", sql_code_md, table_df

    def _save_view(self, view_name: str, set_id: int):
        view_name = view_name.strip()
        if not view_name:
            return gr.Warning("VIEW adı boş olamaz.")
        try:
            resp = self._post("/save_view", {"view_name": view_name, "set_id": set_id}, timeout=30)
            data = resp.json()
            if data.get("status") == "success":
                return gr.Success(data["msg"])
            return gr.Warning("❌ " + data.get("msg", "Bilinmeyen hata"))
        except Exception as e:
            return gr.Warning(f"❌ İstemci hatası: {e}")

    # ───────────────────────── UI Oluştur / Başlat ──────────────────────────
    def launch(self, *, server_name: str = "127.0.0.1", server_port: int = 7860):
        with gr.Blocks(title="Endüstriyel Veri Sorgulama",
                       theme=BLUE_THEME,
                       css=CSS_OVERRIDES) as demo:
            gr.Markdown("### Doğal Dil → SQL Demo (Chat & VIEW)")

            table_df = gr.Dataframe(
            value=pd.DataFrame(),      # boş başlasın
            visible=False,             # ilk açılışta gizli
            label="Sorgu Sonucu",      # sekmede görünen başlık
            interactive=False          # kullanıcı tabloyu değiştirmesin
        )

            set_sel = gr.Dropdown(
                choices=[("1 – Fabrika Yapısı", 1),
                         ("2 – Hammadde Verisi", 2),
                         ("3 – Hat Performansı", 3)],
                value=2,
                label="Tablo Seti",
            )

            with gr.Tabs():
                # ─── SEKME 1: Chat ───
                with gr.Tab("Chat"):
                    chat = gr.Chatbot(label="Sohbet", height=500)
                    txt = gr.Textbox(label="Soru", lines=3, placeholder="Sorunuzu yazın…")
                    send_btn = gr.Button("Gönder", variant="primary")

                # ─── SEKME 2: VIEW Oluştur ───
                with gr.Tab("VIEW Oluştur"):
                    sql_code_md = gr.Markdown(value="", visible=False)
                    view_name_box = gr.Textbox(label="VIEW adı",
                                               placeholder="ör. my_summary_view")
                    save_btn = gr.Button("VIEW'i Kaydet", variant="secondary")

            # Event bağlama
            send_btn.click(
                fn=self._talk,
                inputs=[chat, txt, set_sel, sql_code_md, table_df],
                outputs=[chat, txt, sql_code_md, table_df],

            )

            save_btn.click(
                fn=self._save_view,
                inputs=[view_name_box, set_sel],
                outputs=None,  # modal mesaj döner
            )

        demo.launch(server_name=server_name, server_port=server_port)
