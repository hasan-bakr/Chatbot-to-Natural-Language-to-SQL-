# app/models/rag_model.py  –  tek dosyada 3 şema + 3 Bad/Good seçimi

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, inspect
from urllib.parse import quote_plus
import re, textwrap, time, contextlib, os
from typing import Dict, List
from dotenv import load_dotenv
import os
from openai import AzureOpenAI
from .db_helper import get_engine
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')

# OpenAI istemcisi örneği
openai_client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    api_base=OPENAI_API_BASE
)
# ───────────────────── Açıklamalı Şema Blokları ───────────────────────
DDL_BLOCKS = {
    1: """\
CREATE TABLE Factory (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
);

CREATE TABLE Area (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    FactoryId    INT           NOT NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    CONSTRAINT FK_Area_Factory
        FOREIGN KEY (FactoryId) REFERENCES Factory(Id)
);

CREATE TABLE Line (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    AreaId       INT           NOT NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    CONSTRAINT FK_Line_Area
        FOREIGN KEY (AreaId) REFERENCES Area(Id)
);

CREATE TABLE Station (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    LineId       INT           NOT NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    CONSTRAINT FK_Station_Line
        FOREIGN KEY (LineId) REFERENCES Line(Id)
);

CREATE TABLE Unit (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    StationId    INT           NOT NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    CONSTRAINT FK_Unit_Station
        FOREIGN KEY (StationId) REFERENCES Station(Id)
);

CREATE TABLE Machine (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    BrandId      INT           NULL,
    ModelId      INT           NULL,
    UnitId       INT           NOT NULL,
    SapCode      INT           NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    CONSTRAINT FK_Machine_Unit
        FOREIGN KEY (UnitId) REFERENCES Unit(Id)
);

CREATE TABLE Plc (
    Id           INT           NOT NULL PRIMARY KEY,
    Definition   VARCHAR(50)   NOT NULL,
    MachineId    INT           NOT NULL,
    BrandId      INT           NULL,
    ModelId      INT           NULL,
    IpAddress    VARCHAR(16)   NULL,
    CreateDate   DATETIME      NOT NULL DEFAULT GETDATE(),
    UpdateDate   DATETIME      NULL,
    Status       TINYINT       NOT NULL DEFAULT 1,
    PlcType      TINYINT       NULL,
    CONSTRAINT FK_Plc_Machine
        FOREIGN KEY (MachineId) REFERENCES Machine(Id)
);

CREATE TABLE PlcTag (
    Id                          INT             NOT NULL PRIMARY KEY,
    FactoryId                   INT             NOT NULL,
    PlcId                       INT             NOT NULL,
    Title                       VARCHAR(100)    NOT NULL,
    TagName                     VARCHAR(100)    NOT NULL,
    MinValue                    VARCHAR(50)     NULL,
    MaxValue                    VARCHAR(50)     NULL,
    Value                       VARCHAR(50)     NULL,
    IsAlarm                     BIT             NOT NULL DEFAULT 0,
    SmsNotification             BIT             NOT NULL DEFAULT 0,
    MailNotification            BIT             NOT NULL DEFAULT 0,
    NotificationCycleCounter    INT             NULL,
    NotificationCycleValue      INT             NULL,
    NotificationTimeValue       INT             NULL,
    NotificationTransmissionTime DATETIME       NULL,
    AlarmValue                  VARCHAR(50)     NULL,
    NotificationType            TINYINT         NULL,
    CreatedDate                 DATETIME        NOT NULL DEFAULT GETDATE(),
    UnitTypeId                  INT             NULL,
    CONSTRAINT FK_PlcTag_Factory FOREIGN KEY (FactoryId) REFERENCES Factory(Id),
    CONSTRAINT FK_PlcTag_Plc     FOREIGN KEY (PlcId)     REFERENCES Plc(Id)
);

""",
    2: """\
-- DDL: Pursu_hammadde_verileri
CREATE TABLE [dbo].[Pursu_hammadde_verimleri] (
    [Id]                           INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [Seri_No]                      INT             NOT NULL,
    [Malzeme_kodu]                 VARCHAR(20)     NOT NULL,
    [Malzeme_adi]                  VARCHAR(100)    NOT NULL,
    [Devralinan_miktar]            INT             NULL,
    [Depo_giris_adedi]             INT             NULL,
    [Kullanilan_miktar]            INT             NULL,
    [Fire]                         INT             NULL,
    [Toplam_kullanilan]            INT             NULL,
    [Kalan_miktar]                 INT             NULL,
    [Euro_palet_kullanim]          DECIMAL(18,3)   NULL,
    [Üretilebilecek_palet_euro]    INT             NULL,
    [Standart_palet_kullanim]      DECIMAL(18,3)   NULL,
    [Üretilebilecek_palet_standart] INT            NULL,
    [Gunluk_kullanim]              DECIMAL(18,3)   NULL,
    [Üretilebilecek_palet_gunluk]  INT             NULL,
    [date_time]                    DATETIME        NOT NULL
);

""",
    3: """\

-- DDL: Pursu_hat_verileri
CREATE TABLE [dbo].[Pursu_hat_verileri] (
    [Id]                          INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [hat_name]                    NVARCHAR(50)    NOT NULL,
    [urun1_deger]                 INT             NULL,
    [urun_aciklama]               NVARCHAR(100)   NULL,
    [urun2_deger]                 INT             NULL,
    [urun2_aciklama]              NVARCHAR(100)   NULL,
    [urun3_deger]                 INT             NULL,
    [urun3_aciklama]              NVARCHAR(100)   NULL,
    [uretim_zamani_dk]            INT             NULL,
    [net_uretim_zamani_dk]        INT             NULL,
    [teknik_uretim_zamani_dk]     INT             NULL,
    [operasyonel_verimlilik]      FLOAT           NULL,
    [uretim_verimlilik]           FLOAT           NULL,
    [kapasite_kullanim_orani]     FLOAT           NULL,
    [teknik_durus_kayip_orani]    FLOAT           NULL,
    [date]                        DATE            NOT NULL,
    [date_time]                   DATETIME        NOT NULL
);
"""
}

# ───────────────────── Bad ↔ Good Örnekleri 3 Set ──────────────────────
BAD_GOOD_BLOCKS = {
    1: """
-- ❌ KÖTÜ: Eksik JOIN → AreaName NULL olabilir
SELECT L.Definition AS LineName
FROM Line L
JOIN Station S ON S.LineId = L.Id;

-- ✅ İYİ: Sadece Machine tablosu
SELECT M.Id, M.Definition
FROM Machine M

-- ❌ KÖTÜ: BETWEEN üst sınırı belirsiz
SELECT *
FROM PlcTag PT
WHERE PT.CreatedDate BETWEEN '2025-06-01' AND '2025-06-30';

-- ✅ İYİ: Takvimsel aralık
SELECT *
FROM PlcTag PT
WHERE PT.CreatedDate >= '2025-06-01'
  AND PT.CreatedDate <  '2025-07-01';
""".strip(),
    2: """
-- (Hammadde seti için örnekler buraya)
""".strip(),
    3: """
-- (Hat verisi seti için örnekler buraya)
""".strip()
}


# app/models/rag_model.py  – Azure OpenAI ile (yerel Llama yok)

# --- RULES ---
RULES = {1:"""
### KESİN SQL KURALLARI

1. **DDL UYUM ZORUNLULUĞU**
   - SADECE aşağıda verilen DDL'de tanımlı tablo ve sütunları kullan!
   - Yasaklı sütun örnekleri:
     • ❌ `{table}.Name` → ✅ `{table}.Definition`
     • ❌ `{table}.Updated` → ✅ `{table}.UpdateDate`
     • ❌ `{table}.Created` → ✅ `{table}.CreateDate`
   - Eğer bir sütun DDL'de yoksa:
     1. Hata mesajı ekle: "[HATA: <sütun> DDL'de tanımlı değil]"
     2. DDL'deki gerçek sütun adını kullan

2. **JOIN HİYERARŞİSİ**
   - Kesin JOIN sırası:
     ```Factory → Area → Line → Station → Unit → Machine → Plc → PlcTag```
   - Eksik JOIN yapma (Örn: Factory'den direkt Line'a atlama)
   - Gereksiz JOIN ekleme (Tek tablo sorgularında)

3. **SORGU SAFLIĞI**
   - Tek bir MSSQL SELECT sorgusu (; ile bitmeli)
   - `WITH` CTE kullanımına izin var
   - Yasaklı ifadeler: 
     ```INSERT/UPDATE/DELETE/EXEC/ALTER/MERGE```

4. **KOLON REFERANSLARI**
   - Her sütun `<alias>.<sütun>` formatında olmalı
   - Geçerli örnekler:
     • ✅ `F.Definition`
     • ✅ `PT.TagName`
     • ❌ `Definition` (alias yok)
     • ❌ `Name` (DDL'de yok)

5. **ÖZEL DURUM KURALLARI**
   - Tarih aralıkları:
     ```sql
     -- ❌ Kötü
     WHERE CreatedDate BETWEEN '2025-01-01' AND '2025-01-31'
     
     -- ✅ İyi
     WHERE CreatedDate >= '2025-01-01' 
       AND CreatedDate < '2025-02-01'
     ```
   - Rastgele kayıt:
     ```sql
     -- PostgreSQL'deki LIMIT yerine
     SELECT TOP (5) * FROM Table ORDER BY NEWID()
     ```

6. **ÖRNEKLERLE PEKİŞTİRME**
   ```sql
   -- ✅ DDL'ye uygun örnek
   SELECT M.Id, M.Definition 
   FROM Factory F
   JOIN Machine M ON F.Id = M.UnitId
   WHERE F.Definition = 'Fabrika A';
   
   -- ❌ Yaygın hatalar
   SELECT F.Name FROM Factory F  -- Name DDL'de yok!
   SELECT * FROM Machine LIMIT 5  -- LIMIT geçersiz!

7. **İSİM KURALLARI**
    - Eğer farklı isimler diye bir istek varsa, istenen tablonun Definition sütununu farklı olarak algıla
    - Örnek: Bana farklı isimli fabrikaları ver. 
    - Olması gereken SQL: 
        WITH Fabrikalar AS (
        SELECT DISTINCT F.Definition AS FabrikaAdi
        FROM Factory F
        )
        SELECT FabrikaAdi
        FROM Fabrikalar;
    Bunu sadece Factory tablosu üzerinde yapma!!

8. **FİLTRE UYGULAMASI**
    - Eğer belirli bir filtreleme isteniyorsa, bunu hangi tabloda yapacağını sorudan anla.
    - Örnek: Bana Line ismi "polikarbon damacana hatti" olan Makineleri listele.
    - Olması gereken SQL: 
    SELECT M.Id, M.Definition
    FROM Machine  M
    JOIN Unit     U ON U.Id     = M.UnitId
    JOIN Station  S ON S.Id     = U.StationId
    JOIN Line     L ON L.Id     = S.LineId
    WHERE L.Definition = 'polikarbon damacana hatti';
    - Bu örnekte Line tablosu üzerinde filtreleme istendiği için Line tablosu üzerinde filtreleme yapıldı. Sen de bu şekilde filtreleme yapabilirsin.

9. NUMERIC KARŞILAŞTIRMALAR
    - Bir kolon VARCHAR/NVARCHAR ise ve sayıyla
      karşılaştırılacaksa:
        TRY_CONVERT(decimal(18,3),
                    REPLACE(<alias>.<kolon>, ',', '.'))
    - Direkt “kolon < 50” yazmak yasak!

OTOMATİK DÜZELTME MEKANİZMASI

Eğer DDL ihlali tespit edilirse:

Hatanın tam yerini göster

Doğru sütun öner

Sorguyu otomatik yeniden oluştur
""".strip(),
    2: """""".strip(),
    3: """""".strip()}


# ───────────────────────────── LLModel ──────────────────────────────
class LLModel:
    """
    NL → MSSQL  (gpt-35-turbo, gpt-4o, … Azure OpenAI) 
    """
    def __init__(self, *, table_set: int = 1,
                 endpoint: str | None = None,
                 api_key: str | None = None,
                 deployment: str | None = None):
        if table_set not in {1, 2, 3}:
            raise ValueError("table_set 1, 2 veya 3 olmalı")
        
        # ─── Azure OpenAI istemcisi ───
        load_dotenv()
        endpoint   = endpoint   or os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key    = api_key    or os.getenv("AZURE_OPENAI_KEY")
        deployment = deployment or os.getenv("AZURE_DEPLOYMENT_NAME")

        if not all([endpoint, api_key, deployment]):
            raise ValueError("Azure OpenAI .env bilgileri eksik "
                             "(AZURE_OPENAI_ENDPOINT / KEY / DEPLOYMENT_NAME).")

        self.client          = AzureOpenAI(
            azure_endpoint = endpoint,
            api_key        = api_key,
            api_version    = "2023-12-01-preview"
        )
        self.deployment_name = deployment

        # ─── DB / Şema ───
        self.engine      = get_engine(fast=True)
        self.ddl_block   = DDL_BLOCKS[table_set]
        self.bad_good    = BAD_GOOD_BLOCKS[table_set]
        self.rules       = RULES[table_set]

    # ───────────── PROMPT OLUŞTURMA ─────────────
    def _prompt_messages(self, question: str) -> List[dict]:
        user_prompt = textwrap.dedent(f"""
            {RULES}                          
            
            ### KÖTÜ–İYİ ÖRNEKLER (BAD ↔ GOOD)
            {self.bad_good}

            Sadece MSSQL SELECT sorgusu yaz.

            ### SORU
            {question}

            ### DDL TABLO BLOĞU // BU DDL'E SADIK KALINACAK
            {self.ddl_block}

            SQL:
        """).strip()
        return [
            {"role": "system",
             "content": "You are an expert SQL generator for Microsoft SQL Server."},
            {"role": "user", "content": user_prompt}
        ]

    # ───────────── PARANTEZ / ; DÜZELTİCİ ─────────────
    @staticmethod
    def _post_fix(sql: str) -> str:
        return sql.strip().rstrip(';') + ';'

    # ───────────── NL → SQL ─────────────
    def nl_to_sql(self, question: str) -> str:
        response = self.client.chat.completions.create(
            model       = self.deployment_name,
            temperature = 0.0,
            max_tokens  = 256,
            messages    = self._prompt_messages(question),
        )
        print(response)
        raw = response.choices[0].message.content

        # ```sql …``` bloğunu veya ilk SELECT'i yakala
        m = re.search(r"```sql\s*([\s\S]*?)```", raw, re.I)
        if not m:
            m = re.search(r"\bSELECT[\s\S]+?;", raw, re.I)
        if not m:
            raise ValueError("Model SELECT döndürmedi:\n" + raw[:400])

        sql = m.group(1) if m.lastindex else m.group(0)
        return self._post_fix(sql)

    # ───────────── GÜVENLİ SELECT ÇALIŞTIR ─────────────
    SAFE_RE = re.compile(r"(?i)^\s*(select|with)\b")
    BAD_RE  = re.compile(r"(?i)\b(insert|update|delete|alter|drop|create|merge|exec|into|truncate)\b")

    def _is_safe(self, sql: str) -> bool:
        sql_nc = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.M|re.S).strip()
        return (sql_nc.count(";") <= 1 and
                self.SAFE_RE.match(sql_nc) and
                not self.BAD_RE.search(sql_nc))

    def _columns_exist(self, sql: str) -> bool:
        inspector    = inspect(self.engine)
        # yalnızca dbo şemasındaki tabloları geçerli kabul et
        valid_tables = {t.lower() for t in inspector.get_table_names(schema='dbo')}

        # schema prefix (örn. dbo.) varsa önce temizlemek istersen şu satırı aç:
        # sql = re.sub(r'\b\w+\.', '', sql)

        for tbl, col in re.findall(r'([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)', sql):
            # dbo ya da alias gibi geçersiz isimleri atla
            if tbl.lower() not in valid_tables:
                continue
            # sadece geçerli tablo üzerinde kolon kontrolü yap
            cols = {c['name'].lower()
                    for c in inspector.get_columns(tbl, schema='dbo')}
            if col.lower() not in cols:
                return False
        return True

    def execute_safe(self, sql: str):
        if not self._columns_exist(sql):
            raise ValueError("Model olmayan kolon üretti, SQL yürütülmedi.")
        if not self._is_safe(sql):
            raise ValueError("Yalnız SELECT sorgularına izin var.")
        with contextlib.closing(self.engine.raw_connection()) as conn:
            cur   = conn.cursor()
            cur.execute(sql)
            cols  = [d[0] for d in cur.description]
            rows  = [dict(zip(cols, r)) for r in cur.fetchall()]
            return rows

    # ───────────── Kamu API'si ─────────────
    def answer(self, question: str, *, debug=False) -> Dict:
        t0  = time.perf_counter()
        try:
            sql = self._post_fix(self.nl_to_sql(question))
            gen_ms = (time.perf_counter() - t0) * 1000
            rows = self.execute_safe(sql)
            exec_ms = (time.perf_counter() - t0 - gen_ms/1000) * 1000

            if debug:
                print("SQL →", sql)
                print("Rows→", rows[:5] if rows else "(yok)")

            return {"status": "success",
                    "sql": sql,
                    "rows": rows,
                    "gen_ms": round(gen_ms,1),
                    "exec_ms": round(exec_ms,1)}

        # ⇣—— HER TÜRLÜ HATA BURADA YAKALANIR ————————————
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ─── Hızlı test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    rag = LLModel(table_set=1)    # env değişkenleri .env’den okunur
    res = rag.answer("Bana Fabrikaları ve bu fabrikaların Makinelerini ver.", debug=True)
    print(res["sql"])
    #print(res["rows"][:5])
