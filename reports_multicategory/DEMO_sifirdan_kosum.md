# Sıfırdan canlı koşum — 15 ürün, 3 kategori

Bu akış deponun **hiçbir hazır dosyasını kullanmaz**. Ürünler sunum sırasında
Akakçe'den kazınır, o kazınan dosya işlenir, kalite kapısından geçirilir,
anahtar kelimeler ondan üretilir ve dört yöntem o anahtar kelimelerle arama
yapar. Her adım yeni bir dosya yazar; her adımdan sonra o dosya açılır.

Bütün çıktı `tmp/canli/` altına gider. `data/`, `results/` ve `reports/`
dizinlerine dokunulmaz.

**Ölçülen toplam süre:** kazıma 31 s + işleme/kapı/anahtar kelime ~2 s +
dört yöntem 12,7 dk (ya da üç ürünle 113 s). **Ölçülen maliyet:** 0,00615 USD.

**Neden 3 kategori × 5 ürün.** Kazıma süresi ve model maliyeti kategori
sayısıyla artıyor, ve listeleme sitesi uzun oturumları hız sınırına takıyor.
On kategoriyi eksik toplamaktansa üç kategoriyi tam toplamak hem hızlı hem
dürüst. Seçilen üç kategori kasten birbirinden uzak: telefon (ölçülen en kolay
kategori), kedi maması ve bisküvi (ölçülen en zor iki gruptan biri).

---

## Hazırlık

```powershell
$env:NANO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
$env:AGENTIC_PLANNER_MODEL = "google/gemma-4-26b-a4b-it"
```

Ücretsiz katmandaki ortak Google havuzu tıkanabiliyor; bu iki satır ücretli uç
noktaya geçirir. Terminali kapatırsan tekrar gir.

---

## 1. Kazıma — ürünleri sunum sırasında topla

Girdi: `data/reference/product_categories.csv` (taksonomi)

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider selenium --site akakce --categories elektronik_cep_telefonu,petshop,supermarket --limit-per-category 5 --min-per-category 5 --delay 3 --output tmp\canli\raw.csv
```

**Ölçülen:** 31 saniye, 15 ürün, 3/3 kategori, bot koruması devreye girmedi.
Ekranda Chrome açılıp Akakçe'de üç arama yapıyor.

Üretilen dosyaları aç:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\raw.metadata.json
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\raw.csv --limit 3
```

**Anlatım:** "Taksonomi hangi kategoriden kaç ürün toplanacağını, ürün
kimliklerinin hangi önekle başlayacağını ve her kategorinin hangi nitelikleri
taşıması gerektiğini söylüyor. Kazıyıcı buna göre arama yapıyor, ilan
başlığını ayrıştırıyor ve her satıra ilanın kendi ürün URL'sini yazıyor.
Metadata dosyasındaki `acquisition_mode: scraped` damgası bu verinin
üretilmediğinin kaydı; sentetik üretebilen bir yolumuz da var ama o dosya
`synthetic` damgası taşır ve bir test bu damganın kaybolmasını engeller."

---

## 2. Veri işleme — az önce kazınan dosyayı işle

Girdi: **1. adımın yazdığı** `tmp/canli/raw.csv`

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory --input tmp\canli\raw.csv --output-directory tmp\canli
```

**Ölçülen:** `Valid products: 15`, `Invalid products: 0`.

Üretilen üç dosya:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\processed_products_multicategory.json --limit 2
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\validation_issues_multicategory.csv --limit 5
```

**Anlatım:** "İşleme üç şey yapıyor: şemayı doğruluyor, metni tek kalıba
sokuyor — boşluk kırpma, kontrollü sözlük sütunlarını kanonik yazıma eşleme —
ve satır düzeyinde doğruluyor: eksik zorunlu alan, HTTPS olmayan URL, kategori
kuralına uymayan nitelik. Sorunlu satırlar ayrı bir dosyaya yazılıyor, veri
kümesinden sessizce düşürülmüyor. Burada o dosya boş, çünkü kazıyıcı zaten
temiz satır yazıyor."

Üç kategorinin `attributes` sütunu farklı — asıl gösterilecek şey bu:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\processed_products_multicategory.csv --limit 15 --fields product_id,category_group,attributes
```

**Anlatım:** "Eski şema telefon içindi: `storage_gb`, `ram_gb`, `battery_mah`
zorunluydu, bir bisküvi doğrulamadan geçemezdi. Yeni şemada zorunlu çekirdek
küçük, geri kalanı `attributes` sütununda ve kategori grubuna göre ayrı
doğrulanıyor. Telefonda `storage_gb`, mamada `weight_kg` ve `animal_type`,
bisküvide `net_weight_g` var; üçünde de `variant_label` var, arama sorgusunu
ayırt edici yapan alan o."

---

## 3. Kalite kapısı — işlenmiş dosyayı denetle

Girdi: **2. adımın yazdığı** `tmp/canli/processed_products_multicategory.csv`

```powershell
.\.venv\Scripts\python.exe src\quality_check.py --dataset multicategory --input tmp\canli\processed_products_multicategory.csv --categories elektronik_cep_telefonu,petshop,supermarket --min-per-category 5
```

**Ölçülen çıktı:**

```
Unique product IDs: 15
Missing product IDs: 0
Duplicate ID rows: 0
Duplicate product variant rows: 0
Rows without source URL: 0
Rows with invalid source URL: 0
Category groups with wrong counts: 0

  elektronik_cep_telefonu        5/50 <- below target
  petshop                        5/50 <- below target
  supermarket                    5/50 <- below target

Dataset-level quality check: PASSED
```

**Anlatım:** "Bu kapı satır değil, veri kümesi düzeyinde bakıyor: kimlikler
benzersiz mi, aynı ürün iki kimlikle iki kez girmiş mi, her satırın HTTPS
kaynak URL'si var mı, kategori başına sayı tutuyor mu. `5/50 <- below target`
satırı da bilerek duruyor: kapı bu koşumda 5'lik tabanla çalışıyor ama rapor
her kategoriyi taksonomi hedefine karşı göstermeye devam ediyor, yani eksiklik
gizlenmiyor."

**Önemli nüans, sorulursa:** bu kapı akışı programatik olarak durdurmuyor.
Çıkış kodu veriyor, devam kararını çalıştıran insan veriyor.

---

## 4. Anahtar kelime üretimi

Girdi: **2. adımın yazdığı** `tmp/canli/processed_products_multicategory.json`

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input tmp\canli\processed_products_multicategory.json --limit 15 --output tmp\canli\keywords.json --provider fake
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\keywords.json --limit 5
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\keywords.metadata.json
```

**Anlatım:** "Ürün başına tek anahtar kelime. Kelime `variant_label` üzerinden
kuruluyor, o yüzden telefonda da mamada da bisküvide de çalışıyor. Metadata
dosyası hangi üretecin kullanıldığını kaydediyor."

Aynı 15 ürünü canlı dil modeliyle de üretip yan yana koy — bu, raporun
**Tablo 3a** bulgusunu canlı tekrar eder:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input tmp\canli\processed_products_multicategory.json --limit 5 --output tmp\canli\keywords_live.json --provider openrouter
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\keywords_live.json --limit 5
```

**Anlatım:** "Canlı model bazı ürünlerde ayırt edici niteliği düşürüyor — renk,
tat, 'kısırlaştırılmış' gibi ibareler. Hepsi aynı markanın başka ürününe
götürebilecek bilgi. Deneyde deterministik şablonu seçmemizin sebebi bu, ve
bu bir tercih değil ölçüm: 20 ürünün 7'sinde canlı model bilgi kaybediyor,
korunum %100'e karşı %92,2."

---

## 5. Dört yöntem — URL toplama ve uygunluk yargısı

Girdi: **2. adımın yazdığı** ürün listesi ve **4. adımın yazdığı** anahtar
kelimeler. Ara dönüşüm yok; `--subset` hangi ürünlerin koşulacağını söyleyen
dosyayı alıyor ve bu dosya CSV de olabilir JSON da.

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset tmp\canli\processed_products_multicategory.json --keywords tmp\canli\keywords.json --execution-mode live --limit 3 --max-results 5 --save --results-directory tmp\canli\results --skip-existing
```

**Ekranda ne olur:** Chrome tekrar tekrar açılıp Bing'de arama yapıyor.
`--skip-existing` sayesinde koşum bölünebilir; yarıda kalırsa aynı komut
kaldığı yerden devam eder, biten işe kota harcamaz.

**Ölçülen (15 ürünün tamamı koşulduğunda: 60 koşum, 0 hata):**

| Yöntem | Koşum | Ortalama süre | Toplam |
|---|---:|---:|---:|
| selenium_rule_based | 15 | 5,5 s | 82 s |
| tavily_llm | 15 | 9,4 s | 141 s |
| selenium_nano_llm | 15 | 11,4 s | 170 s |
| agentic_search | 15 | 24,4 s | 366 s |
| **Toplam** | **60** | | **12,7 dakika** |

296 sonuç, 60/60 dosya şema doğrulamasından geçti, toplam maliyet
**0,00615 USD**. Üç koşum beşten az sonuç döndürdü — arama o kadarını
bulmuş; hat bunu hata saymıyor, dosyaya kaç sonuç geldiyse onu yazıyor.

Yukarıdaki komut üç ürün koşar: ölçülen **113 saniye**, 12 dosya. Canlı toplu
koşum üç ürüne kadar serbesttir, o yüzden onay bayrağı gerekmez.

**Vaktin varsa 15 ürünün tamamı** — ölçülen 12,7 dakika, bu yüzden sunum
sırasında değil, öncesinde koşulur. Aynı komutu sonra tekrar verirsen
`--skip-existing` biteni atlar ve ekranda saniyeler içinde döner:

```powershell
.\.venv\Scripts\python.exe srcun_evaluation_batch.py --subset tmp\canli\processed_products_multicategory.json --keywords tmp\canli\keywords.json --execution-mode live --limit 15 --allow-live-batch --max-results 5 --save --results-directory tmp\canliesults --skip-existing
```

Üretilen dosyaları yöntem yöntem aç:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\results\selenium_rule_based --limit 1 --fields product_id,keyword,method,model,prompt_version,runtime_seconds,estimated_cost_usd
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\results\tavily_llm --limit 1 --fields product_id,method,model,results
```

**Anlatım:** "Dört yönteme de birebir aynı anahtar kelime gitti; değişen tek
şey sonuçların nereden toplandığı ve nasıl yargılandığı. Ve dikkat: yöntemler
'satın alınabilir sayfa' aramıyor. Aramayı yapıp dönen ilk beş sonucu
alıyorlar — haber, inceleme, kategori sayfası, aksesuar, ne gelirse. Sonra her
sonuca 'bu uygun mu' diye yargı veriyorlar. Ölçtüğümüz şey tam olarak bu
yargının ne kadar isabetli olduğu."

Kural tabanlı yöntemin `prompt_version` alanı `not_applicable` — dil modeli
kullanmıyor, güvenilir alan adı tablosu ve anahtar kelime eşleşmesiyle puan
veriyor, 0,60 eşiğini geçen uygun sayılıyor. Bu yüzden hata analizinde kontrol
grubu olabiliyor.

Şema doğrulaması:

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py tmp\canli\results
```

**Ölçülen:** `Total files: 60 / Valid files: 60 / Invalid files: 0`.

### Bu koşumun kendi bulgusu

Yöntemlerin kaç sonuca "uygun" dediğini say:

```powershell
.\.venv\Scripts\python.exe -c "import json,glob,collections;s=collections.defaultdict(lambda:[0,0]);[ (s[d['method']].__setitem__(1,s[d['method']][1]+len(d['results'])), s[d['method']].__setitem__(0,s[d['method']][0]+sum(1 for r in d['results'] if r['predicted_relevant']))) for d in (json.load(open(f,encoding='utf-8')) for f in glob.glob('tmp/canli/results/*/*.json'))];[print('%-22s %3d/%3d  %%%.1f'%(m,v[0],v[1],100*v[0]/v[1])) for m,v in sorted(s.items())]"
```

**Ölçülen çıktı:**

```
agentic_search          74/ 74  %100.0
selenium_nano_llm       75/ 75  %100.0
selenium_rule_based     69/ 72  %95.8
tavily_llm              70/ 75  %93.3
```

**Anlatım:** "Bu, raporun **Bulgu 2**'sinin daha önce hiç görülmemiş, beş dakika
önce toplanmış veride kendiliğinden tekrarlanması. İki dil modeli tabanlı
yöntem sonuçların **%100'üne** uygun dedi — yani hiçbir sonucu reddetmediler.
Bu ilk bakışta 'model bu işi yapamıyor' gibi okunur. Ama biz bunun sebebini
izole ettik: değerlendirici modele sorulan soru, insan etiketleyiciye verilen
kuralla aynı değildi. İstem kategori sayfasını uygun sayıyordu, kural
saymıyordu. İstemi kuralla hizalayınca özgüllük 0,000'den 0,846'ya çıktı ve
kontrol grubu hiç değişmedi."

Bu, demoyu raporun ana bulgusuna bağlayan köprü: taze veri, aynı davranış.

---

## 6. Buradan sonrası neden canlı gösterilemiyor

Sıradaki adım insan etiketlemesi. Çalışma kitabını üretebiliriz:

```powershell
.\.venv\Scripts\python.exe src\evaluation\export_label_workbook.py tmp\canli\results --subset tmp\canli\processed_products_multicategory.json --output tmp\canli\label_workbook.xlsx
```

Excel'de aç ve göster.

**Anlatım:** "Bu kitapta yöntemlerin tahminleri yok — etiketleyene modelin
cevabını göstermek etiketi modele kaydırır. URL'ler de tekilleştirilmiş: aynı
sayfayı dört yöntem de bulmuş olabilir, insan bir kez etiketliyor. Asıl
deneyde 399 sonuç 193 benzersiz URL'ye indi ve iki kişi elle etiketledi. O iş
saatler sürdüğü için burada canlı yapamıyoruz; rapordaki sayılar zaten
etiketlenmiş 20 ürünlük kümeden geliyor."

Rapordaki gerçek ölçüm:

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py reports_multicategory\multicategory_evaluation_metrics.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

---

## 7. Temizlik

`tmp/` dizini `.gitignore` içinde; depoya hiçbir şey karışmaz.

```powershell
git status
```

**Beklenen:** `nothing to commit, working tree clean`.

---

## Adım özeti

| # | Komut | Girdi | Üretilen dosya |
|---|---|---|---|
| 1 | `product_scraper.py` | `product_categories.csv` | `tmp/canli/raw.csv` + `.metadata.json` |
| 2 | `data_processor.py` | 1'in çıktısı | `processed_products_multicategory.csv` / `.json` / `validation_issues_*.csv` |
| 3 | `quality_check.py` | 2'nin çıktısı | — (rapor, ekrana) |
| 4 | `keyword_generator.py` | 2'nin çıktısı | `keywords.json` + `keywords.metadata.json` |
| 5 | `run_evaluation_batch.py` | 2'nin ve 4'ün çıktısı | `results/<yontem>/*.json` |
| 6 | `export_label_workbook.py` | 5'in çıktısı | `label_workbook.xlsx` |
