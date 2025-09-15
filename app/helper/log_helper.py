import json
from datetime import datetime
import os

class LogManager:
    def __init__(self, log_file="query_logs.json"):
        self.log_file = log_file
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Log dosyasının varlığını kontrol eder ve yoksa oluşturur"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def log_interaction(self, query, response):
        """
        Kullanıcı sorusu ve sistem cevabını loglar
        
        Args:
            query (str): Kullanıcının sorduğu soru
            response (dict/str): Sistemin verdiği cevap
        """
        try:
            # Mevcut logları oku
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)

            # Yeni log kaydı
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response
            }

            # Logları güncelle
            logs.append(log_entry)

            # Güncellenmiş logları kaydet
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Loglama hatası: {str(e)}")

    def get_recent_logs(self, limit=10):
        """
        Son log kayıtlarını getirir
        
        Args:
            limit (int): Getirilecek log sayısı
            
        Returns:
            list: Son log kayıtları
        """
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            return logs[-limit:]
        except Exception as e:
            print(f"Log okuma hatası: {str(e)}")
            return [] 