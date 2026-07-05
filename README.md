# AnamurMuzİş 🍌

Anamur (Mersin) muz sektörü için iş ilanı uygulaması.

- **İşverenler** muz bahçesi/tesisi için iş ilanı verir (hasat, paketleme, dikim, bakım…).
- **İşçiler** müsaitliklerini, deneyimlerini ve beklenen ücretlerini paylaşır.
- İlanlar iş türüne göre filtrelenebilir ve metin araması yapılabilir.
- Her ilanda tek dokunuşla arama (`tel:` bağlantısı) bulunur.

## Çalıştırma

Bağımlılık yoktur; sadece Python 3 gerekir:

```bash
python3 server.py
```

Ardından tarayıcıda **http://localhost:8756** adresini açın.

## Teknik notlar

- `server.py` — Python standart kütüphanesiyle yazılmış HTTP sunucusu.
  Statik dosyaları `docs/` klasöründen sunar; `/api/jobs` ve `/api/workers`
  uç noktaları GET (listeleme) ve POST (yeni kayıt) destekler.
- `data.json` — tüm ilanların saklandığı dosya. İlk çalıştırmada örnek
  verilerle otomatik oluşturulur. Sıfırlamak için silmeniz yeterli.
- `docs/` — Türkçe, mobil uyumlu tek sayfa arayüz (saf HTML/CSS/JS).
  Klasör adı `docs` olduğu için GitHub Pages üzerinden doğrudan
  yayınlanabilir; API yoksa arayüz otomatik olarak tarayıcı
  depolamasına (localStorage) geçer — canlı demo bu modda çalışır.

## Yol haritası fikirleri

- Telefonla doğrulama / basit üyelik
- İlan süresi dolunca otomatik kaldırma
- WhatsApp ile iletişim bağlantısı
- Mahalle/köy bazlı konum filtresi
