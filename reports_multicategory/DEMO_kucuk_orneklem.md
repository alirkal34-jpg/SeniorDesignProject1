# Küçük örneklem üzerinde adım adım pipeline

Üç ürünle (`ELK001` iPhone, `PET001` kedi maması, `SPM001` bisküvi) hattın
tamamı: ham veri → işleme → anahtar kelime → URL toplama → doğrulama →
etiketleme → metrik. Üç ürün üç ayrı kategoriden seçilmiştir, çünkü asıl
gösterilmek istenen şey hattın tek bir ürün tipine bağlı olmaması.

Her adımda **çalıştır** komutu ve hemen ardından **göster** komutu vardır.
Göster komutu dosyayı okur, yazmaz. PyCharm'da dosyayı Project ağacından
çift tıklayıp editörde de açabilirsin — göster komutu projeksiyonda daha
okunaklı olduğu için var.

Bütün yeni çıktılar `tmp/demo/` altına yazılır. `results/` ve `reports/`
dizinlerine dokunulmaz; orası dondurulmuş telefon deneyinin yeri.

Ölçülen toplam süre: **hazırlık hariç yaklaşık 2,5 dakika**, tamamı canlı.
Ölçülen toplam maliyet: **0,0004 USD**.

---

## Hazırlık (sunumdan önce, bir kez)

PyCharm terminalini aç, proje kökünde olduğundan emin ol.

```powershell
$env:NANO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
$env:AGENTIC_PLANNER_MODEL = "google/gemma-4-26b-a4b-it"
```

Ücretsiz katmandaki ortak Google havuzu tıkanabiliyor; bu iki satır ücretli uç
noktaya geçirir. Terminali kapatırsan tekrar gir.

Başka hazırlık yok. Her adım doğrudan deponun kendi dosyalarını okur; ara
dosya kesilmez, kopya çıkarılmaz.

Üç ürün her komutta `--ids ELK001,PET001,SPM001` ile ismen seçilir.
`--limit N` seçeneği dosyanın **ilk N kaydını** alır ve bu veri kümesinin ilk
üçü ELK001, ELK002, ELK003 — üçü de iPhone. Kimlikleri saymak, üç ayrı
kategoriyi tek koşumda göstermenin yolu. Dosyada olmayan ya da etiketli alt
küme dışında kalan bir kimlik verilirse komut sessizce atlamaz, hata verip
durur.

---

## 1. Ham veri — nereden geldi

Bu adımda **hiçbir işlem çalışmaz**. İki mevcut dosya ekrana basılır; amaç,
verinin nereden geldiğini iddia etmek yerine göstermektir.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\raw\candidate_products_multicategory.metadata.json
```

**Ne görünecek:** `"acquisition_mode": "scraped"`, kaynak `akakce`, toplama
tarihi, kategori başına ürün sayısı. Bu dosyayı kazıyıcı 18.08.2026'da yazdı;
komut onu yalnızca okuyor.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\raw\candidate_products_multicategory.csv --limit 2 --fields product_id,product_name,brand,category_group,source_url
```

**Ne görünecek:** her satır ilanın kendi HTTPS ürün URL'sini taşıyor.

**Anlatım:** "Sentetik veri üretebilen bir yolumuz da var, ama o dosya
`acquisition_mode: synthetic` damgası taşır ve bir test bu damganın sessizce
kaybolmasını engeller. Raporda kullanılan her sayı `scraped` damgalı veriden
gelir."

**İsteğe bağlı — kazımayı canlı göstermek.** Ölçülen süre 240 saniye ve
kategori sekizinde site bot korumasını devreye sokuyor; sunumda çalıştırma,
ama sorulursa çıktısı hazır:

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider selenium --site akakce --limit-per-category 1 --min-per-category 1 --delay 3 --output tmp\demo\raw_small.csv
```

Bu koşum 7 kategoriyi topladı, 8.'de `bot protection hit` verip 45 ve 90
saniye bekledi, sonra durdu ve `--resume` önerdi. Kanıtı:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\raw_small.metadata.json
```

**Anlatım:** "Bot korumasını aşmaya çalışmıyoruz. Site hayır dediğinde kod
duruyor, ne topladıysa kaydediyor ve nereden devam edeceğini söylüyor. Bu da
bir sonuç: ticari siteler otomatik toplamayı fiilen engelliyor."

---

## 2. Veri işleme — şema doğrulama ve temizleme

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory
```

**Ne görünecek:** `489 valid, 0 invalid`.

Şimdi bu komutun **az önce yazdığı** dosyayı aç. 489 kaydın tamamı ekrana
sığmayacağı için üç kategoriden üçünü seçiyoruz — gösterilen, hattın gerçekten
ürettiği dosyanın kendisi, kopyası değil:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --fields product_id,product_name,category_group,attributes
```

**Ölçülen çıktı:**

| Ürün | Kategori | attributes |
|---|---|---|
| ELK001 | elektronik_cep_telefonu | `{"storage_gb": 256, "variant_label": "256 GB"}` |
| PET001 | petshop | `{"animal_type": "Kedi", "variant_label": "10 kg", "weight_kg": 10.0}` |
| SPM001 | supermarket | `{"net_weight_g": 114, "variant_label": "114 gr"}` |

**Anlatım:** "Asıl mesele bu tablo. Eski şema telefon içindi: `storage_gb`,
`ram_gb`, `battery_mah` zorunluydu, o yüzden bir bisküvi doğrulamadan
geçemezdi. Yeni şemada zorunlu çekirdek küçük, geri kalan her şey `attributes`
sütununda ve kategori grubuna göre ayrı doğrulanıyor. Üç ürünün üç farklı
alan kümesi taşıdığını görüyorsunuz, ama üçünde de `variant_label` var — arama
sorgusunu ayırt edici yapan alan o."

Doğrulama raporu:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\processed\validation_issues_multicategory.csv --limit 3
```

**Ne görünecek:** `toplam satir: 0` — yalnızca başlık satırı var.

**Anlatım:** "Sıfır sorunlu satır. Bu, doğrulamanın çalışmadığı anlamına
gelmiyor; kazıyıcı zaten temiz satır yazıyor. Doğrulamanın neyi yakaladığını
test paketinde görebilirsiniz: eksik `source_url`, HTTPS olmayan URL, kategori
kuralına uymayan nitelik."

---

## 3. Anahtar kelime üretimi — iki üreteç, aynı üç ürün

Bu adım raporun **Tablo 3a** bulgusunu canlı tekrar eder.

Önce deterministik şablon (API kullanmaz):

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --output tmp\demo\keywords_fake.json --provider fake
```

Sonra canlı dil modeli (aynı üç ürün, tek istek):

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input data\processed\processed_products_multicategory.json --ids ELK001,PET001,SPM001 --output tmp\demo\keywords_live.json --provider openrouter
```

İkisini yan yana göster:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_fake.json --limit 3
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_live.json --limit 3
```

**Ölçülen fark:**

| Ürün | Deterministik şablon | Canlı model |
|---|---|---|
| ELK001 | iPhone 17 256 GB **Siyah** fiyat | Apple iPhone 17 256 GB fiyat |
| PET001 | Pro Plan Somonlu 10 kg **Kısırlaştırılmış** Yetişkin Kedi Maması fiyat | Pro Plan Somonlu Kedi Maması 10 kg fiyat |
| SPM001 | Eti Burçak Sütlü Çikolatalı Bisküvi 114 gr fiyat | Eti Burçak Sütlü Çikolatalı Bisküvi 114 gr fiyat |

**Anlatım:** "Canlı model iki üründe ayırt edici niteliği düşürdü: telefonun
rengini ve mamanın 'kısırlaştırılmış' ibaresini attı. İkisi de aynı markanın
farklı ürününe götürebilecek bilgi. Deneyde deterministik şablonu tercih
etmemizin sebebi bu ve bu bir tercih değil, ölçüm: 20 ürünün 7'sinde canlı
model bilgi kaybediyor, korunum oranı %100'e karşı %92,2."

Maliyet ve model bilgisi de dosyada:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\keywords_live.metadata.json
```

**Ölçülen:** `runtime_seconds: 11.26`, `estimated_cost_usd: 5.255e-05`.

---

## 4. URL toplama — dört yöntem, üç ürün, canlı

Tek komut; ekranda Chrome açılıp Bing'de arama yapıyor.

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset data\evaluation\evaluation_subset_multicategory.csv --keywords tmp\demo\keywords_fake.json --ids ELK001,PET001,SPM001 --execution-mode live --max-results 5 --save --results-directory tmp\demo\results --skip-existing
```

**Ölçülen:** 12 koşum (3 ürün × 4 yöntem), **113 saniye**, `failed_count: 0`.

**Anlatım:** "Dört yönteme de birebir aynı anahtar kelime gidiyor; farklı olan
tek şey sonuçların nasıl toplandığı ve nasıl yargılandığı. `--skip-existing`
sayesinde koşum bölünebilir: sağlayıcının günlük kotası dolarsa kalan yerden
devam ediyor, biten işe kota harcamıyor."

Şimdi dört yöntemin aynı ürün için ne bulduğunu tek tek göster:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\results\selenium_rule_based --limit 1 --fields product_id,keyword,method,model,runtime_seconds,estimated_cost_usd
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\results\tavily_llm --limit 1 --fields product_id,method,model,prompt_version,runtime_seconds,results
```

**Ne görünecek:** her sonuçta `domain`, `url`, `title`, `snippet`,
`predicted_relevant`, `relevance_score`. Kural tabanlı yöntemin
`prompt_version` alanı `not_applicable`, çünkü dil modeli kullanmıyor.

**Anlatım:** "Her dosya kendisini üreten şeyi kaydediyor: sağlayıcı, model,
istem sürümü, süre, maliyet. Bir sayıyı altı ay sonra sorgulayacak biri hangi
koşulda üretildiğini dosyadan okuyabiliyor."

Şema doğrulaması:

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py tmp\demo\results
```

**Ölçülen:** `Total files: 12 / Valid files: 12 / Invalid files: 0`.

---

## 5. Etiketleme — model tahminleri gizlenerek

```powershell
.\.venv\Scripts\python.exe src\evaluation\export_label_workbook.py tmp\demo\results --output tmp\demo\label_workbook_small.xlsx
```

Üretilen Excel'i PyCharm yerine Excel'de aç.

**Anlatım:** "Bu çalışma kitabında yöntemlerin tahminleri **yok**.
Etiketleyene modelin cevabı gösterilmiyor, yoksa etiket modelin cevabına
kayar. Kitapta bir de yönerge sayfası var; uygunluk kuralı orada yazılı."

Gerçek deneyin 193 etiketi:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py data\labels\multicategory_ground_truth.csv --limit 3 --fields product_id,url,human_relevant,notes
```

**Dikkat çekilecek nokta:** `method` sütunu boş. Etiket URL'ye ait, yöntemin
değil — aynı URL'yi dört yöntem de bulmuş olabilir ve etiket hepsinde aynıdır.

---

## 6. Ölçüm — küçük örneklem neden rapora giremiyor

```powershell
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py --results-directory tmp\demo\results --ids ELK001,PET001,SPM001 --output tmp\demo\manifest_small.json
```

**Ölçülen:** `Result files: 12 / Methods: 4`.

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py --manifest tmp\demo\manifest_small.json --output tmp\demo\metrics_small.json
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py --manifest tmp\demo\manifest_small.json --output tmp\demo\category_metrics_small.json --markdown tmp\demo\category_metrics_small.md
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\demo\metrics_small.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

**Ölçülen çıktı:**

```
product_count               : 3
experiment_count            : 12
result_count                : 60
labeled_result_count        : 50
ground_truth_coverage_ratio : 0.8333
accuracy                    : 0.76
```

Şimdi rapor üretmeyi dene — **kasten**:

```powershell
.\.venv\Scripts\python.exe src\evaluation\multicategory_report.py --metrics tmp\demo\metrics_small.json --category-metrics tmp\demo\category_metrics_small.json --output tmp\demo\report_small.md
```

**Ölçülen çıktı:**

```
[ERROR] The comparison report requires complete ground-truth coverage; got 0.8333.
```

**Anlatım:** "Demonun en önemli anı bu. Az önce yaptığımız canlı koşum yeni
URL'ler getirdi ve bunların 10'u hiç etiketlenmemiş; kapsam %83,3. Doğruluk
%76 çıkıyor — gerçek deneyin %76,19'una çok yakın — ama araç bu sayıyı rapora
yazmayı **reddediyor**. Çünkü eksik etiketli bir kümeden çıkan doğruluk,
etiketlenmemiş sonuçların ne olduğuna bağlı olarak her yöne gidebilir.
Raporda kullandığımız sayı, kapsamı %100 olan dondurulmuş 80 koşumdan
geliyor."

Gerçek ölçüm o kümeden:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py reports_multicategory\multicategory_evaluation_metrics.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

**Ölçülen:** 20 ürün, 80 koşum, 399 sonuç, 399 etiketli, kapsam 1.0, doğruluk
0.7619.

---

## 7. Zincirin tamamı tutuyor mu

```powershell
.\.venv\Scripts\python.exe src\evaluation\check_consistency.py
```

**Ne görünecek:** on başlık, hepsi `[OK ]`, `SONUC: tutarsizlik bulunmadi`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py"
```

**Ne görünecek:** `Ran 371 tests ... OK (skipped=1)`, yaklaşık 1,1 saniye.

---

## Sunumdan sonra temizlik

`tmp/` dizini `.gitignore` içindedir, depoya hiçbir şey karışmaz. Yine de
kontrol:

```powershell
git status
```

**Beklenen:** `nothing to commit, working tree clean`.

---

## Adım özeti

| # | Adım | Komut çıktısı | Gösterilecek dosya |
|---|---|---|---|
| 1 | Ham veri | — | `data/raw/candidate_products_multicategory.metadata.json` |
| 2 | Veri işleme | 489 valid, 0 invalid | `data/processed/processed_products_multicategory.json` |
| 3 | Anahtar kelime | 2 dosya | `tmp/demo/keywords_fake.json` + `keywords_live.json` |
| 4 | URL toplama | 12 koşum, 113 s | `tmp/demo/results/<yontem>/` |
| 5 | Etiketleme | 193 etiket | `data/labels/multicategory_ground_truth.csv` |
| 6 | Ölçüm | kapsam %83,3 → rapor reddedildi | `tmp/demo/metrics_small.json` |
| 7 | Denetim | 10 başlık OK, 371 test | — |
