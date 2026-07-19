# AnamurMuzİş — Claude Code proje rehberi

Anamur (Mersin) muz sektörü için canlı, gerçek kullanıcıları olan iş ilanı
sitesi. İşverenler ilan verir, işçiler müsaitlik bildirir. Arayüz Türkçedir;
kullanıcı kitlesi telefonla gezen tarım işçileri ve bahçe sahipleridir —
sadelik ve mobil uyum her karardan önce gelir.

## Mimari (tamamı ücretsiz katmanlar)

- **Alan adı:** https://anamurmuzis.com — Cloudflare Registrar + DNS
  (cellek'in Cloudflare hesabı). `www` kaydı Cloudflare proxy'li (turuncu
  bulut), apex kayıtları DNS-only; bunu değiştirme — GitHub'ın sertifikası
  yalnız apex'i kapsıyor.
- **Barındırma:** GitHub Pages, `main` dalındaki `docs/` klasöründen.
  `main`'e push = ~1 dk içinde canlı. Ayrı deploy adımı yok, build yok.
- **Veritabanı:** Supabase (Postgres), proje `wsnodkkvyubtvqcxrspl`,
  cellek'in Supabase hesabında. Bağlantı bilgileri `docs/config.js`
  içinde — anon key bilinçli olarak herkese açıktır, güvenlik RLS'tedir.
- **Yönetim paneli yok:** ilan silme/düzenleme Supabase Dashboard →
  Table Editor üzerinden yapılır.

## Kod düzeni

- `docs/` — sitenin tamamı: saf HTML/CSS/JS, framework yok, build yok.
  - `app.js` — tüm mantık. Veri katmanı sıralı: Supabase → yerel Python
    API → localStorage (çevrimdışı yedek). DB snake_case, uygulama
    camelCase; `JOB_COLS`/`WORKER_COLS` takma adları ve `jobToRow`/
    `workerToRow` dönüştürücüleri bu çeviriyi yapar.
  - `config.js` — Supabase URL + anon key.
  - `CNAME` — özel alan adı; silme.
- `server.py` — yalnız yerel geliştirme (bağımlılıksız, Python stdlib).
  Çalıştır: `python3 server.py` → http://localhost:8756
- `supabase/schema.sql` — tablolar, RLS politikaları, örnek veri.
  Şema değişikliği = bu dosyayı güncelle + Dashboard SQL Editor'de çalıştır.
- `.github/workflows/keep-alive.yml` — günlük DB ping'i (ücretsiz planın
  7 gün hareketsizlik duraklatmasına karşı). Silme.
- `.github/workflows/backup.yml` — her Pazartesi tüm ilanları `backups/`
  klasörüne JSON olarak işler. `backups/` dosyalarını elle düzenleme.

## Güvenlik modeli

RLS: herkes okuyabilir ve ekleyebilir; istemciden update/delete YOK
(politika tanımlı değil). Bu bilinçli bir tasarım — değiştirmeden önce
spam/istismar etkisini düşün.

## Kurallar

- UI metinleri Türkçe; kod yorumları Türkçe.
- Bağımlılık ekleme (npm, framework, build aracı) — bu proje bilinçli
  olarak sıfır bağımlılıklı.
- `main`'e push canlıya çıkar: küçük, test edilmiş değişiklikler yap.
  Görsel değişiklikleri yerel sunucuda doğrula.
- Paylaşım metinleri (`SITE_URL`) https://anamurmuzis.com/ kullanır.
- Tek üretim veritabanı var; şema değişikliklerini ekip içinde koordine et.

## Yol haritası (sıradaki işler)

1. **Spam koruması (Katman 1):** Postgres trigger'ları — telefon/IP
   başına günlük ilan limiti, 24 saat içinde aynı başlık+telefon
   tekrarını reddet, metinlerde URL engelle. + "Şikayet et" düğmesi
   (`reports` tablosu).
2. **İlan süresi:** 14 gün sonra ilanların listeden düşmesi (varsayılan
   2 hafta olarak kararlaştırıldı).
3. İleride gerekirse: Cloudflare Turnstile (bot artarsa), telefonla
   giriş / Supabase Auth (istismar büyürse; SMS maliyetli, aceleye gerek yok).
