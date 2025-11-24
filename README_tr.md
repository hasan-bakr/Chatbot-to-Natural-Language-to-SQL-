# Chatbot-to-Natural-Language-to-SQL

Bu proje, doğal dilde yazılan sorguları SQL sorgularına dönüştüren bir chatbot uygulamasıdır. Endüstriyel veri sorgulama ve üretim hattı modellemesi için örnek tablo şemaları içerir. Gerçek şirket verisi veya ticari/hassas bilgi içermez.

## Klasör Yapısı
- `app/`
  - `app.py`: Ana uygulama dosyası
  - `helper/`
    - `api_helper.py`: SQL şemaları ve yardımcı fonksiyonlar
    - `interface_helper.py`: Arayüz ve veri işleme yardımcıları
    - `log_helper.py`: Loglama yardımcıları

## Özellikler
- Doğal dilden SQL sorgusu üretimi
- Endüstriyel veri modeli (Factory, Area, Line, vb.)
- Gerçek veri içermez, örnek şemalar ve test amaçlı kodlar içerir

## Kurulum
1. Gerekli Python paketlerini yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
2. Uygulamayı başlatın:
   ```bash
   python app/app.py
   ```

## Notlar
- Proje test ve demo amaçlıdır.
- Şirket veya müşteri verisi içermez.
- SQL şemaları örnek olarak sunulmuştur.

---
Geliştirici: Hasan Bakr
