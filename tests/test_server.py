#!/usr/bin/env python3
"""server.py için testler — yalnız Python standart kütüphanesi kullanır.

Çalıştırma (depo kökünden):  python3 -m unittest discover -s tests -v

Bu dosya mevcut davranışı sabitler. Bilinçli olarak *bugünkü* davranışı
doğrular; Supabase şemasıyla ayrıştığı yerler test adlarında ve
yorumlarda "ayrışma" olarak işaretlenmiştir (bkz. supabase/schema.sql).
"""
import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sunucuyu_yukle():
    """server.py'yi modül olarak yükler (__main__ koruması sayesinde güvenli)."""
    spec = importlib.util.spec_from_file_location(
        "anamur_server", os.path.join(BASE_DIR, "server.py")
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


srv = _sunucuyu_yukle()

# Geçerli bir iş ilanı gövdesi — testler bunu kopyalayıp değiştirir.
GECERLI_ILAN = {
    "title": "Muz hasadı için işçi aranıyor",
    "employer": "Test Tarım",
    "location": "Ören",
    "workType": "Hasat",
    "wage": "Günlük 900 TL",
    "phone": "0532 000 00 99",
}

GECERLI_ISCI = {
    "name": "Test İşçi",
    "location": "Anamur Merkez",
    "phone": "0532 000 00 98",
    "workTypes": ["Hasat"],
}


class CleanStrTest(unittest.TestCase):
    """clean_str: boşluk sadeleştirme, kırpma ve tür dönüşümü."""

    def test_ardisik_bosluklar_tek_bosluga_iner(self):
        self.assertEqual(srv.clean_str("Muz   hasadı", 120), "Muz hasadı")

    def test_satir_sonu_ve_sekme_de_bosluk_sayilir(self):
        self.assertEqual(srv.clean_str("Muz\n\thasadı", 120), "Muz hasadı")

    def test_bas_ve_son_bosluklar_kirpilir(self):
        self.assertEqual(srv.clean_str("  Anamur  ", 120), "Anamur")

    def test_max_len_uzunlugunda_kesilir(self):
        self.assertEqual(srv.clean_str("x" * 200, 10), "x" * 10)

    def test_turkce_karakterler_bozulmaz(self):
        self.assertEqual(srv.clean_str("İşçi ÇĞÖŞÜ ıi", 120), "İşçi ÇĞÖŞÜ ıi")

    def test_sadece_bosluktan_olusan_deger_bosalir(self):
        self.assertEqual(srv.clean_str("   \n  ", 120), "")

    def test_none_bos_metne_donusur(self):
        self.assertEqual(srv.clean_str(None, 10), "")

    def test_sayi_metne_donusur(self):
        self.assertEqual(srv.clean_str(12345, 10), "12345")

    def test_sozluk_metne_donusur_ayrisma(self):
        # AYRIŞMA: JSON nesnesi gönderilirse reddedilmez, Python repr'ine
        # dönüşüp kaydedilir. Supabase text sütunu böyle bir değeri almaz.
        self.assertEqual(srv.clean_str({"a": 1}, 40), "{'a': 1}")


class ValidateTest(unittest.TestCase):
    """validate: zorunlu alan denetimi ve alan bazlı uzunluk sınırları."""

    def test_bos_payload_tum_zorunlu_alanlari_bildirir(self):
        item, errors = srv.validate({}, srv.JOB_FIELDS)
        self.assertEqual(
            sorted(errors),
            sorted(["title", "employer", "location", "workType", "wage", "phone"]),
        )
        # Hata olsa bile tüm alanlar item içinde yer alır.
        self.assertEqual(set(item), set(srv.JOB_FIELDS))

    def test_gecerli_payload_hatasizdir(self):
        item, errors = srv.validate(GECERLI_ILAN, srv.JOB_FIELDS)
        self.assertEqual(errors, [])
        self.assertEqual(item["title"], GECERLI_ILAN["title"])

    def test_opsiyonel_alanlar_bos_birakilabilir(self):
        _, errors = srv.validate(GECERLI_ILAN, srv.JOB_FIELDS)
        self.assertNotIn("description", errors)
        self.assertNotIn("duration", errors)
        self.assertNotIn("startDate", errors)

    def test_sadece_bosluk_iceren_zorunlu_alan_eksik_sayilir(self):
        payload = dict(GECERLI_ILAN, title="     ")
        _, errors = srv.validate(payload, srv.JOB_FIELDS)
        self.assertIn("title", errors)

    def test_uzun_baslik_120_karaktere_kirpilir(self):
        payload = dict(GECERLI_ILAN, title="a" * 500)
        item, errors = srv.validate(payload, srv.JOB_FIELDS)
        self.assertEqual(errors, [])
        self.assertEqual(len(item["title"]), 120)

    def test_uzun_aciklama_600_karaktere_kirpilir(self):
        payload = dict(GECERLI_ILAN, description="a" * 5000)
        item, _ = srv.validate(payload, srv.JOB_FIELDS)
        self.assertEqual(len(item["description"]), 600)

    def test_isci_alanlari_workTypes_icermez(self):
        # workTypes create_item içinde ayrıca işlenir; alan tablosunda yoktur.
        self.assertNotIn("workTypes", srv.WORKER_FIELDS)
        item, errors = srv.validate(GECERLI_ISCI, srv.WORKER_FIELDS)
        self.assertEqual(errors, [])
        self.assertNotIn("workTypes", item)

    def test_tanimsiz_alanlar_yok_sayilir(self):
        payload = dict(GECERLI_ILAN, isAdmin=True, ekstra="x")
        item, _ = srv.validate(payload, srv.JOB_FIELDS)
        self.assertNotIn("isAdmin", item)
        self.assertNotIn("ekstra", item)


class VeriDosyasiTest(unittest.TestCase):
    """load_data / save_data: tohumlama ve atomik yazma."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self._eski = srv.DATA_FILE
        srv.DATA_FILE = os.path.join(self.tmpdir.name, "data.json")
        self.addCleanup(lambda: setattr(srv, "DATA_FILE", self._eski))

    def test_dosya_yoksa_tohum_veriyle_olusturulur(self):
        data = srv.load_data()
        self.assertEqual(len(data["jobs"]), len(srv.SEED["jobs"]))
        self.assertTrue(os.path.exists(srv.DATA_FILE))

    def test_tohum_verisi_kopyalanir_referans_paylasilmaz(self):
        # load_data SEED'in kopyasını döndürmeli; aksi hâlde bir isteğin
        # eklediği ilan SEED'e sızar ve sonraki tohumlamaya karışır.
        data = srv.load_data()
        data["jobs"].append({"id": "kirletme"})
        self.assertEqual(len(srv.SEED["jobs"]), 2)

    def test_yazilip_okunan_veri_ayni_kalir(self):
        veri = {"jobs": [{"id": "1", "title": "Muz hasadı işçisi"}], "workers": []}
        srv.save_data(veri)
        self.assertEqual(srv.load_data(), veri)

    def test_turkce_karakterler_dosyada_kacisiz_saklanir(self):
        srv.save_data({"jobs": [{"title": "İşçi aranıyor"}], "workers": []})
        with open(srv.DATA_FILE, encoding="utf-8") as f:
            self.assertIn("İşçi aranıyor", f.read())

    def test_yazma_sonrasi_gecici_dosya_kalmaz(self):
        srv.save_data({"jobs": [], "workers": []})
        self.assertFalse(os.path.exists(srv.DATA_FILE + ".tmp"))


class ApiTest(unittest.TestCase):
    """Gerçek HTTP sunucusu üzerinden uçtan uca API testleri."""

    @classmethod
    def setUpClass(cls):
        # Test çıktısını kirletmemek için istek günlüğünü sustur.
        cls._eski_log = srv.Handler.log_message
        srv.Handler.log_message = lambda *a, **k: None

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        # 127.0.0.1 istekleri ortamdaki proxy'ye uğramamalı.
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        srv.Handler.log_message = cls._eski_log

    def setUp(self):
        # Her test taze tohum veriyle başlasın.
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self._eski = srv.DATA_FILE
        srv.DATA_FILE = os.path.join(self.tmpdir.name, "data.json")
        self.addCleanup(lambda: setattr(srv, "DATA_FILE", self._eski))

    # ---------- yardımcılar ----------
    def _url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def _get(self, path):
        with self.opener.open(self._url(path), timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def _post(self, path, payload=None, govde=None):
        veri = govde if govde is not None else json.dumps(payload).encode("utf-8")
        istek = urllib.request.Request(
            self._url(path), data=veri,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with self.opener.open(istek, timeout=10) as res:
                return res.status, json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as hata:
            return hata.code, json.loads(hata.read().decode("utf-8"))

    # ---------- GET ----------
    def test_ilanlar_en_yeniden_eskiye_siralanir(self):
        durum, ilanlar = self._get("/api/jobs")
        self.assertEqual(durum, 200)
        tarihler = [i["createdAt"] for i in ilanlar]
        self.assertEqual(tarihler, sorted(tarihler, reverse=True))

    def test_isciler_en_yeniden_eskiye_siralanir(self):
        durum, isciler = self._get("/api/workers")
        self.assertEqual(durum, 200)
        tarihler = [i["createdAt"] for i in isciler]
        self.assertEqual(tarihler, sorted(tarihler, reverse=True))

    def test_sorgu_dizesi_yok_sayilir(self):
        durum, _ = self._get("/api/jobs?foo=bar")
        self.assertEqual(durum, 200)

    def test_statik_dosyalar_docs_klasorunden_servis_edilir(self):
        with self.opener.open(self._url("/index.html"), timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("AnamurMuz", res.read().decode("utf-8"))

    # ---------- POST /api/jobs ----------
    def test_gecerli_ilan_201_ile_kaydedilir(self):
        durum, kayit = self._post("/api/jobs", GECERLI_ILAN)
        self.assertEqual(durum, 201)
        self.assertTrue(kayit["id"])
        self.assertTrue(kayit["createdAt"])
        self.assertEqual(kayit["title"], GECERLI_ILAN["title"])

    def test_kaydedilen_ilan_listede_gorunur(self):
        self._post("/api/jobs", GECERLI_ILAN)
        _, ilanlar = self._get("/api/jobs")
        self.assertIn(GECERLI_ILAN["title"], [i["title"] for i in ilanlar])

    def test_eksik_zorunlu_alan_400_doner(self):
        eksik = dict(GECERLI_ILAN)
        del eksik["phone"]
        durum, govde = self._post("/api/jobs", eksik)
        self.assertEqual(durum, 400)
        self.assertEqual(govde["fields"], ["phone"])

    def test_basarisiz_kayit_veriyi_degistirmez(self):
        _, once = self._get("/api/jobs")
        self._post("/api/jobs", {})
        _, sonra = self._get("/api/jobs")
        self.assertEqual(len(once), len(sonra))

    def test_isci_sayisi_alt_sinira_cekilir(self):
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, workersNeeded=0))
        self.assertEqual(kayit["workersNeeded"], 1)

    def test_isci_sayisi_ust_sinira_cekilir(self):
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, workersNeeded=5000))
        self.assertEqual(kayit["workersNeeded"], 999)

    def test_sayi_olmayan_isci_sayisi_bire_duser(self):
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, workersNeeded="abc"))
        self.assertEqual(kayit["workersNeeded"], 1)

    def test_bos_isci_sayisi_bire_duser(self):
        # Formdan boş gelen sayı alanı "" olarak iletilir.
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, workersNeeded=""))
        self.assertEqual(kayit["workersNeeded"], 1)

    def test_isci_sayisi_hic_verilmezse_bir_olur(self):
        _, kayit = self._post("/api/jobs", GECERLI_ILAN)
        self.assertEqual(kayit["workersNeeded"], 1)

    def test_isci_sayisi_tamsayi_olarak_doner(self):
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, workersNeeded="7"))
        self.assertIsInstance(kayit["workersNeeded"], int)
        self.assertEqual(kayit["workersNeeded"], 7)

    def test_gecersiz_tarih_kabul_edilir_ayrisma(self):
        # AYRIŞMA: server.py tarih biçimini denetlemez; Supabase'de
        # start_date sütunu `date` türünde olduğu için aynı gövde
        # üretimde reddedilir. Yerel geliştirme üretimden daha gevşek.
        _, kayit = self._post("/api/jobs", dict(GECERLI_ILAN, startDate="tarih-degil"))
        self.assertEqual(kayit["startDate"], "tarih-degil")

    # ---------- POST /api/workers ----------
    def test_gecerli_isci_201_ile_kaydedilir(self):
        durum, kayit = self._post("/api/workers", GECERLI_ISCI)
        self.assertEqual(durum, 201)
        self.assertEqual(kayit["workTypes"], ["Hasat"])

    def test_is_turu_secilmezse_400_doner(self):
        durum, govde = self._post("/api/workers", dict(GECERLI_ISCI, workTypes=[]))
        self.assertEqual(durum, 400)
        self.assertEqual(govde["fields"], ["workTypes"])

    def test_bos_metinlerden_olusan_is_turleri_reddedilir(self):
        durum, _ = self._post("/api/workers", dict(GECERLI_ISCI, workTypes=["  ", ""]))
        self.assertEqual(durum, 400)

    def test_tekil_is_turu_listeye_cevrilir(self):
        _, kayit = self._post("/api/workers", dict(GECERLI_ISCI, workTypes="Hasat"))
        self.assertEqual(kayit["workTypes"], ["Hasat"])

    def test_is_turleri_en_fazla_altiyla_sinirlanir(self):
        cok = ["tur%d" % i for i in range(20)]
        _, kayit = self._post("/api/workers", dict(GECERLI_ISCI, workTypes=cok))
        self.assertEqual(len(kayit["workTypes"]), 6)

    def test_is_turu_kirk_karaktere_kirpilir(self):
        _, kayit = self._post("/api/workers", dict(GECERLI_ISCI, workTypes=["x" * 100]))
        self.assertEqual(len(kayit["workTypes"][0]), 40)

    # ---------- hatalı istekler ----------
    def test_bilinmeyen_uc_nokta_404_doner(self):
        durum, govde = self._post("/api/bilinmeyen", {})
        self.assertEqual(durum, 404)
        self.assertIn("error", govde)

    def test_bozuk_json_400_doner(self):
        durum, govde = self._post("/api/jobs", govde=b"{bozuk json")
        self.assertEqual(durum, 400)
        self.assertIn("error", govde)

    def test_bos_govde_400_doner(self):
        durum, _ = self._post("/api/jobs", govde=b"")
        self.assertEqual(durum, 400)

    def test_gecersiz_utf8_400_doner(self):
        durum, _ = self._post("/api/jobs", govde=b"\xff\xfe\x00")
        self.assertEqual(durum, 400)

    def test_json_dizisi_gonderilirse_400_doner(self):
        # Liste gövdesi .get() çağrısında patlamamalı, düzgün hata dönmeli.
        durum, _ = self._post("/api/jobs", [1, 2, 3])
        self.assertEqual(durum, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
