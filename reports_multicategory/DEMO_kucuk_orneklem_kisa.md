# Küçük örneklem demo — ekran paylaşımı sürümü

Komutları buradan kopyala, PowerShell'e yapıştır. Bu dosya ekranda görünecek,
o yüzden anlatım kısa. Gerekçe/senaryo metni için: `DEMO_kucuk_orneklem.md`.

## Hazırlık — sunumdan HEMEN önce, bu terminalde

```powershell
$env:NANO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
$env:AGENTIC_PLANNER_MODEL = "google/gemma-4-26b-a4b-it"
```

**Kontrol:** `echo $env:NANO_LLM_MODEL` → sonunda `:free` **olmamalı**. Terminali
kapatırsan bu iki satırı tekrar çalıştır.

---

### 1. Ham veri kaynağı

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\raw\candidate_products_multicategory.metadata.json
```

**Bak:** `"acquisition_mode": "scraped"`, kaynak `akakce`

### 2. Ham veri — örnek satırlar

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\raw\candidate_products_multicategory.csv --limit 2 --fields product_id,product_name,brand,category_group,source_url
```

**Bak:** her satırda `https://` ile başlayan gerçek ürün URL'si

### 3. Veri işleme — şema doğrulama

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory
```

**Bak:** `489 valid, 0 invalid`

### 4. İşlenmiş veri — 3 ürün, 3 kategori

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --fields product_id,product_name,category_group,attributes
```

**Bak:** 3 farklı `attributes` seti (storage_gb / weight_kg+animal_type / net_weight_g) — hepsinde `variant_label` var

### 5. Doğrulama raporu

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\processed\validation_issues_multicategory.csv --limit 3
```

**Bak:** `toplam satir: 0`

### 6. Anahtar kelime — deterministik (API yok)

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --output tmp\demo\keywords_fake.json --provider fake
```

**Üretir:** `tmp\demo\keywords_fake.json`

### 7. Anahtar kelime — canlı model

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --output tmp\demo\keywords_live.json --provider openrouter
```

**Üretir:** `tmp\demo\keywords_live.json` (1 canlı API çağrısı)

### 8-9. İkisini karşılaştır

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_fake.json --limit 3
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_live.json --limit 3
```

**Bak:** ELK001'de "Siyah", PET001'de "Kısırlaştırılmış" — canlı model bu ayırt
edici kelimeleri düşürüyor mu?

### 10. Canlı modelin maliyeti

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_live.metadata.json
```

**Bak:** `runtime_seconds`, `estimated_cost_usd`

### 11. URL toplama — 4 yöntem, canlı (Chrome açılacak)

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset data\evaluation\evaluation_subset_multicategory.csv --keywords tmp\demo\keywords_fake.json --ids ELK001,PET001,SPM001 --execution-mode live --max-results 5 --save --results-directory tmp\demo\results --skip-existing
```

**Bak:** 12 koşum (3 ürün × 4 yöntem), `failed_count: 0`

### 12-13. Bir yöntemin çıktısı

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\results\selenium_rule_based --limit 1 --fields product_id,keyword,method,model,runtime_seconds,estimated_cost_usd
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\results\tavily_llm --limit 1 --fields product_id,method,model,prompt_version,runtime_seconds,results
```

**Bak:** her sonuçta `domain, url, title, snippet, predicted_relevant,
relevance_score`; kural tabanlının `prompt_version`'ı `not_applicable`

### 14. Şema doğrulaması

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py tmp\demo\results
```

**Bak:** `Valid files: 12 / Invalid files: 0`

### 15. Etiketleme çalışma kitabı

```powershell
.\.venv\Scripts\python.exe src\evaluation\export_label_workbook.py tmp\demo\results --output tmp\demo\label_workbook_small.xlsx
```

**Üretir:** `tmp\demo\label_workbook_small.xlsx` — Excel'de aç, `predicted_relevant`/`relevance_score` sütunu **yok**

### 16. Gerçek deneyin 193 etiketi

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\labels\multicategory_ground_truth.csv --limit 3 --fields product_id,url,human_relevant,notes
```

**Bak:** `method` sütunu boş — etiket URL'ye ait, yönteme değil

### 17. Manifest (bu 3 ürün için)

```powershell
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py --results-directory tmp\demo\results --ids ELK001,PET001,SPM001 --output tmp\demo\manifest_small.json
```

**Bak:** `Result files: 12 / Methods: 4`

### 18-19. Metrikler

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py --manifest tmp\demo\manifest_small.json --output tmp\demo\metrics_small.json
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py --manifest tmp\demo\manifest_small.json --output tmp\demo\category_metrics_small.json --markdown tmp\demo\category_metrics_small.md
```

**Üretir:** `metrics_small.json`, `category_metrics_small.json`

### 20. Metrikleri göster

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\metrics_small.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

**Bak:** `ground_truth_coverage_ratio: 0.8333` (100 değil!), `accuracy: 0.76`

### 21. Rapor üretmeyi dene — KASTEN REDDEDİLECEK

```powershell
.\.venv\Scripts\python.exe src\evaluation\multicategory_report.py --metrics tmp\demo\metrics_small.json --category-metrics tmp\demo\category_metrics_small.json --output tmp\demo\report_small.md
```

**Bak:** `[ERROR] ... requires complete ground-truth coverage; got 0.8333.`
→ Demonun can alıcı anı: kapsam %100 değilse araç rapor üretmeyi reddediyor.

### 22. Gerçek (dondurulmuş) 80-koşum sonucu

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py reports_multicategory\multicategory_evaluation_metrics.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

**Bak:** 20 ürün, 80 koşum, 399/399 etiketli, kapsam `1.0`, doğruluk `0.7619`

### 23. Tutarlılık kontrolü ⚠️ bkz. aşağıdaki uyarı

```powershell
.\.venv\Scripts\python.exe src\evaluation\check_consistency.py
```

**Bak:** 10 başlık, hepsi `[OK ]`, `SONUC: tutarsizlik bulunmadi` — **ama şu an
temiz çıkmıyor, sunumdan önce çöz (aşağıya bak).**

### 24. Test paketi

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py"
```

**Bak:** `Ran 427 tests ... OK (skipped=1)`

---

## Sunumdan sonra

```powershell
git status
```

**Bak:** `tmp/` `.gitignore`'da, depoya bir şey karışmamalı.

---

## ⚠️ SUNUMDAN ÖNCE ÇÖZ — adım 23 şu an "1 TUTARSIZLIK" verir

Bu kısa dosyayı hazırlarken kontrol ettim: `check_consistency.py` **şu an**
temiz çıkmıyor.

**Sebep bu demoyla ilgisiz.** Geçen oturumda `tests/test_invariants_lock.py`
eklendi, paket artık 399 değil **427** test içeriyor. `SDP_rapor_TR.md`
hâlâ birkaç yerde "399 test" diyor (satır 275, 338, 735, 1032). Adım 23'ü
şimdi çalıştırırsan:

```
[HATA] raporda geciyor: 427 test
SONUC: 1 TUTARSIZLIK
```

çıkar. Adım 24 (`427 test ... OK`) buna karşılık doğru ve sorunsuz çalışır —
tutarsız olan tek şey raporun eski sayıyı taşıması.

**Seçeneklerin:**
- Rapordaki "399 test" geçen 4 yeri "427 test" olarak güncelle (rapor
  metnini değiştirmek onayını gerektirir, ben tek başıma yapmadım).
- Ya da sunumda adım 23'ü atla / bu bilinen farkı önceden açıkla.
