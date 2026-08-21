# Danışman sunumu — demo akışı

Sıra hâlinde çalıştırılacak komutlar, her adımda ekranda ne görüneceği ve ne
anlatılacağı. Komutlar PowerShell içindir ve proje kökünden çalıştırılır.

Ölçülen toplam komut süresi, canlı adım dâhil yaklaşık bir dakikadır. Konuşma
payıyla 12–15 dakikalık bir demo.

---

## 0. Sunumdan önce (hoca gelmeden, 2 dakika)

Bu adım seyirci önünde yapılmaz.

```powershell
cd C:\Users\Ali\Desktop\SDP\first-task
```

Ücretsiz katmandaki ortak Google havuzu tıkanabiliyor — 22.08.2026 gecesi
denendiğinde dört yöntemin üçü `429 upstream_provider_shared_pool` ile
düşmüştür. Canlı demoyu ücretli uç noktaya sabitleyin; ölçülen maliyet
**koşum başına 0,0004 USD**:

```powershell
$env:NANO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
$env:AGENTIC_PLANNER_MODEL = "google/gemma-4-26b-a4b-it"
```

Bu iki satır yalnızca o terminal oturumunda geçerlidir; `.env` dosyasına
dokunmaz. Terminali kapatırsanız tekrar girin.

Kontrol listesi:

- Chrome kurulu ve kapalı (Selenium kendi penceresini açacak).
- Excel'de açık `~$` kilit dosyası yok.
- `git status` temiz.
- Yedek olarak `tmp\demo_langgraph\` içinde önceki gece üretilmiş gerçek
  canlı çıktı duruyor; internet çökerse onu açıp gösterin.

---

## 1. "Sayılar tutuyor mu?" (30 saniye)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py"
```

**Beklenen:** `Ran 362 tests ... OK (skipped=1)`, yaklaşık 1,2 saniye.

```powershell
.\.venv\Scripts\python.exe src\evaluation\check_consistency.py
```

**Beklenen:** on başlık, hepsi `[OK ]`, son satır `SONUC: tutarsizlik bulunmadi`.

**Anlatım:** "Bu ikinci komut projenin bütün sayı zincirini denetliyor: temel
doğruluk dosyası, sonuç dosyaları, etiket kapsamı, metrik tutarlılığı, kontrol
grubu, rapordaki her sayının metrik dosyalarıyla uyumu, dondurulmuş telefon
deneyi, üretilen raporların yeniden üretilebilirliği ve raporun bildirdiği test
sayısı. Rapordaki bir sayı dosyalardan saparsa bu komut kırmızı veriyor."

---

## 2. Veri: 489 gerçek ürün, 10 kategori (1 dakika)

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory
```

**Beklenen:** 489 geçerli satır, 0 geçersiz.

```powershell
.\.venv\Scripts\python.exe src\quality_check.py --dataset multicategory
```

**Beklenen:** kategori başına ürün sayısı tablosu; dokuz grup 50/50, moda grubu
`39/50 <- below target` ve son satırda **`Dataset-level quality check: FAILED`**.

Bu kırmızı satır beklenen davranıştır, hazırlıksız yakalanmayın. Kaliteyi
denetleyen kapı, hedefin altına düşen bir kategoriyi geçirmiyor.

**Anlatım:** "Veri Akakçe'den kazındı, üretilmedi. Her satır ilanın kendi HTTPS
ürün URL'sini taşıyor ve veri kümesi `acquisition_mode: scraped` damgalı.
Testlerden biri bu damganın sessizce kaybolmasını engelliyor, çünkü sentetik
veriyi gerçek gibi sunmak istemiyoruz. Ekranda gördüğünüz FAILED de tam olarak
bu yüzden duruyor: moda kategorisi 50 yerine 39 üründe kaldı, çünkü o
kategorideki gerçek ilan başlıkları yapılandırılmış teknik özellik
yayınlamıyor. Eksik 11 satırı uydurmak yerine kapının kırmızı kalmasını tercih
ettik; bu, raporda ölçülmüş bir olgu olarak yazılı."

Hoca kapının yeşil hâlini görmek isterse eşiği ölçülen değere indirin:

```powershell
.\.venv\Scripts\python.exe src\quality_check.py --dataset multicategory --min-per-category 39
```

---

## 3. Hattın kendisi, ağa çıkmadan (1 dakika)

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow comparison --execution-mode fake
```

**Beklenen:** dört yöntemin de aynı anahtar kelimeyi aldığı, dördünün de
başarıyla döndüğü JSON; `all_methods_used_same_keyword: true`.

**Anlatım:** "LangGraph ile kurulmuş dört yöntemli karşılaştırma çizgesi. Sahte
sağlayıcılarla çalıştığı için ağ da API anahtarı da gerekmiyor; testlerin kota
tüketmeden çalışabilmesinin sebebi bu. `all_methods_used_same_keyword` alanı
deneyin adilliğini garanti ediyor: dört yönteme de birebir aynı girdi gidiyor."

---

## 4. CANLI KOŞUM — demonun ana anı (2 dakika)

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow end-to-end --product-id ELK001 --products data\processed\processed_products_multicategory.json --keyword-provider openrouter --execution-mode live --max-results 5 --save --workflow-output-directory tmp\demo_sunum
```

**Ekranda ne olur:** Chrome penceresi açılır, Bing'de arama yapılır, kapanır,
tekrar açılır. Ölçülen süre **34 saniye**, ölçülen maliyet **0,00039 USD**.

**Beklenen çıktı (22.08.2026 gecesi ölçülen):**

| Yöntem | Süre | Sonuç | Model |
|---|---:|---:|---|
| selenium_rule_based | 5,5 s | 5 | rule-based-v1 |
| selenium_nano_llm | 9,2 s | 5 | gemma-4-26b |
| tavily_llm | 9,2 s | 5 | gemma-4-26b |
| agentic_search | 10,1 s | 5 | gemma-4-26b |

**Anlatım:** "Tek komut: ürün verisi okunuyor, dil modeli anahtar kelimeyi
üretiyor, aynı anahtar kelime dört yönteme birden gidiyor, sonuçlar
sıralanıyor, süre ve maliyet toplanıyor ve tüm kanıt diske yazılıyor. Chrome'un
açılıp kapanması Selenium'un gerçekten arama yapması. Google yerine Bing
kullanıyoruz: Google otomatik testte CAPTCHA sayfasına düştü ve CAPTCHA'yı
aşacak hiçbir şey yazmadık."

Hoca "başka bir kategoride de göster" derse `--product-id` değiştirin:

| Ürün | Kategori | Neden ilginç |
|---|---|---|
| `SPM001` | Süpermarket | Ölçülen en zor gruplardan biri; çoklu paket ayrımı |
| `SPO001` | Spor / outdoor | Uygun sonuç payı en düşük grup (%56,41) |
| `PET001` | Petshop | Kategori sayfası tuzağının en çok görüldüğü grup |

Sonra üretilen dosyaların şemasını doğrulayın:

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py tmp\demo_sunum\method_results
```

**Beklenen:** `Total files: 4 / Valid files: 4 / Invalid files: 0`.

---

## 5. Ölçüm zinciri baştan sona (2 dakika)

Bu beş komut, rapordaki bütün sayıları etiket dosyalarından yeniden üretir.

```powershell
.\.venv\Scripts\python.exe src\evaluation\import_label_workbook.py --workbook data\labels\label_review_session1.xlsx data\labels\label_review_session2.xlsx --adjudication data\labels\multicategory_label_adjudications.csv --output data\labels\multicategory_ground_truth.csv
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py --manifest data\evaluation\final_evaluation_manifest_multicategory.json --output reports_multicategory\multicategory_evaluation_metrics.json
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\multicategory_report.py
```

Ardından — bu satır demonun en ikna edici anıdır:

```powershell
git status
```

**Beklenen:** `nothing to commit, working tree clean`.

**Anlatım:** "Az önce bütün metrikleri ve raporu sıfırdan yeniden ürettik. Git
hiçbir dosyanın değiştiğini söylemiyor. Yani depodaki sayılar elle yazılmadı,
hesaplandı; ve hesap tekrar edilebilir. Ölçülen toplam süre bir saniyenin
altında."

---

## 6. Ana bulgu — hata analizi (3 dakika, çoğu konuşma)

Önce ilk ölçümün sorununu gösterin:

```powershell
type reports_multicategory\multicategory_category_metrics.md
```

**Anlatım:** "İlk ölçümde genel doğruluk %76,19. Ama özgüllük sütununa bakın:
Selenium + NanoLLM 0,000. Yani uygun olmayan 26 sonuçtan hiçbirini
reddetmemiş. Dengeli doğruluğu 0,5000 — ikili sınıflandırmada tesadüf düzeyi.
İlk okunuşta 'küçük model bu işi yapamıyor' denir."

Sonra teşhisi anlatın:

> Değerlendirici modelin istemi (24.07.2026): *"Relevant means product,
> **category**, marketplace, retailer, or price-comparison intent."*
>
> İnsan etiketleyiciye verilen kural (18.08.2026): *"IRRELEVANT when: it is a
> **category** or search page that does not reach the product."*

"İstem kategori sayfasını uygun sayıyor, kural saymıyor. İki metin farklı
zamanlarda, birbirinden habersiz yazılmış. Model yanlış cevap vermiyordu; ona
başka bir soru soruluyordu."

Kontrollü deneyi gösterin:

```powershell
.\.venv\Scripts\python.exe src\evaluation\rerun_with_aligned_prompt.py
```

**Beklenen:** `zaten mevcut (atlanan): 80`, `toplam dosya: 80/80` — API çağrısı
yapılmaz, çünkü koşum sürdürülebilir ve iş bitmiş durumdadır.

```powershell
type reports_multicategory\prompt_v2_category_metrics.md
```

**Ölçülen sonuçlar:**

| Yöntem | Doğruluk | Özgüllük |
|---|---|---|
| Agentic Search | 0,780 → **0,890** | 0,043 → **0,783** |
| Selenium + NanoLLM | 0,740 → **0,850** | 0,000 → **0,846** |
| Tavily + NanoLLM | 0,820 → **0,850** | 0,393 → **0,750** |
| Selenium + Kural Tabanlı *(kontrol)* | 0,707 → 0,707 | 0,125 → 0,125 |

Genel doğruluk **%76,19 → %82,46**.

**Anlatım:** "Yeni arama yapılmadı; diskteki aynı 399 sonuç, aynı 193 insan
etiketi. Değişen tek şey isteme yazılan ölçüt. Kural tabanlı yöntem dil modeli
kullanmadığı için kontrol grubu ve hiç değişmiyor — nedensellik iddiamızın
dayanağı bu satır. İstem bir kez yazıldı ve bir kez çalıştırıldı; sonuca bakıp
istemi iyileştirseydik istemi test kümesine uydurmuş olurduk."

Dürüstlük payını da söyleyin: "Hizalama temiz bir zafer değil. Üç yöntemde
toplam 73 karar değişti; 49'u doğru yöne, 24'ü yanlış yöne gitti. Yeni istem
bazı geçerli ürün sayfalarını da reddediyor. Küçük modelin kendi sınırları
hizalamadan sonra da görünür."

**Çıkarılan ders (raporun tasarım önerisi):** ölçüt tek bir yerde tanımlanmalı;
hem insan yönergesi hem model istemi o tek kaynaktan türetilmeli.

---

## 7. Hocanın kendi geri bildirimine cevap (1 dakika)

**Anlatım:** "Ara değerlendirmede 'tek kategori genellenebilirliği göstermez'
demiştiniz. Bunu ölçtük. Dört yöntemin ortalamasında telefon kategorisi
**%100,00**, diğer dokuz kategori **%73,52** doğruluk veriyor. Yani yalnızca
telefonla yapılan bir değerlendirme, hattı olduğundan iyi gösteriyordu. Uygun
sonuç payı da kategoriye göre %56,41 ile %95,00 arasında değişiyor. Geri
bildiriminiz raporun en anlamlı bulgularından birini ortaya çıkardı."

Kategori tablosu raporda **Tablo 10**.

---

## 8. Açık işler (1 dakika)

- Raporda 8 adet `[EKSİK VERİ]`: teslim tarihi, çalışma saati kaydı, maliyet
  varsayımları, enerji ölçümü, bölümün etik kodu, kurum iş birliği.
- Şekiller çizilecek (draw.io / PlantUML); ASCII taslak ve düz metin
  açıklamaları hazır.
- Word şablonuna aktarım ve İngilizce çeviri; şablondaki sahte kaynaklar
  (Bass, Jones) rapordaki 12 doğrulanmış IEEE kaynağıyla değiştirilecek.
- Değerlendiriciler arası anlaşma katsayısı hesaplanamıyor: iki oturumun URL
  kümeleri kesişmiyor. Hesaplanabilmesi için ortak bir alt kümenin iki kişi
  tarafından bağımsız etiketlenmesi gerekir.
- Açık soru: `found_by_methods` sütunu etiketleyiciye görünüyor ve dolaylı
  sinyal taşıyor olabilir. Dört yöntemin birden bulduğu 9 URL'nin 9'u uygun;
  tek yöntemin bulduğu 144 URL'de oran %70,1. Yanlılık mı gerçek kalite mi,
  mevcut tasarım ayırt etmiyor.

---

## Riskler ve B planı

| Risk | Belirti | Ne yapılacak |
|---|---|---|
| Ücretsiz havuz tıkalı | `429 upstream_provider_shared_pool` | Adım 0'daki iki `$env:` satırı girilmiş mi kontrol edin |
| Bing CAPTCHA / bot koruması | Selenium sonuç döndürmüyor | Adım 4'ü atlayın, `tmp\demo_langgraph\` içindeki gece üretilmiş gerçek çıktıyı açın |
| İnternet yok | Her canlı adım düşer | Adım 1, 2, 3, 5, 6 tamamen çevrimdışı çalışır; demo yine tam anlaşılır |
| Chrome sürümü uyuşmazlığı | Selenium açılışta hata | Adım 4'ü atlayın; B planı aynı |

**Demoda kullanılmayacak komutlar.** `src\run_tavily_llm.py`,
`src\run_selenium_nano_llm.py`, `src\run_agentic_search.py` ve
`src\run_selenium_rule_based.py` tek başına çalıştırıldığında çıktıyı
**`results\` altına** yazar; orası dondurulmuş telefon deneyinin dizinidir.
Canlı gösterim için yalnızca `langgraph_flow.py --workflow-output-directory` ya
da `run_evaluation_batch.py --results-directory` kullanın.

`demo_dashboard.py` de kullanılmamalıdır: içindeki adımlar 100 ürünlük telefon
deneyine göre yazılmıştır, çok kategorili çalışmayı ve istem hizalama deneyini
göstermez.

---

## Cepte tutulacak sayılar

| Ne | Değer |
|---|---|
| Toplanan ürün | 489, 10 kategori grubu, Akakçe, 18.08.2026 |
| Değerlendirme alt kümesi | 20 ürün (kategori başına 2, farklı markalar) |
| Canlı koşum | 80 (20 ürün × 4 yöntem), 0 hata |
| Arama sonucu | 399 |
| Elle etiketlenen benzersiz URL | 193 (140 uygun / 53 uygunsuz), kapsam %100 |
| Genel doğruluk | %76,19 (v1) → %82,46 (hizalanmış istem) |
| Özgüllük, Selenium + NanoLLM | 0,000 → 0,846 |
| Kontrol grubu (kural tabanlı) | Hiç değişmedi |
| Değişen karar | 73 (49 doğru yöne, 24 yanlış yöne) |
| Telefon vs diğer 9 kategori | %100,00 / %73,52 |
| Dondurulmuş telefon deneyi | %68,84, 199 etiketli sonuç, bozulmadı |
| Test paketi | 362 test, 1 atlandı, 0 hata, ~1,2 s |
| Canlı koşum maliyeti | 0,00039 USD / ürün (ücretli uç nokta) |
