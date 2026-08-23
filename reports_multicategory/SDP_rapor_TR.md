# ÜRÜN VERİSİNDEN ANAHTAR KELİME ÜRETİMİ VE ARAMA SONUÇLARININ E-TİCARET UYGUNLUĞUNUN DÖRT YÖNTEMLE KARŞILAŞTIRILMASI

**COMP491 — Senior Design Project I**

**Öğrenciler:** Atahan Bulut, Ali Rubar Kal
**Danışman:** Tuna Çakar
**Tarih:** **[EKSİK VERİ: teslim tarihi (gg/aa/yyyy)]**

MEF ÜNİVERSİTESİ
MÜHENDİSLİK FAKÜLTESİ
BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ

---

## ABSTRACT

**PRODUCT-DRIVEN KEYWORD GENERATION AND A FOUR-METHOD COMPARISON OF E-COMMERCE RELEVANCE IN SEARCH RESULTS**

Atahan Bulut, Ali Rubar Kal
MEF University, Faculty of Engineering, Department of Computer Engineering
Advisor: Tuna Çakar
AUGUST, 2026

Bu projede, yapılandırılmış ürün verisinden işlemsel (transactional) niyet taşıyan arama sorguları üretilmekte ve bu sorgularla elde edilen web arama sonuçlarının e-ticaret uygunluğu dört farklı yöntemle değerlendirilir. Karşılaştırılan yöntemler şunlardır: Selenium tabanlı toplama ile kural tabanlı alan adı puanlaması, Selenium tabanlı toplama ile küçük ölçekli dil modeli (NanoLLM) değerlendirmesi, Tavily arama API'si ile NanoLLM değerlendirmesi ve planlama–arama–değerlendirme döngüsü kuran etmen tabanlı (agentic) arama. Dört yöntemin tamamı LangGraph üzerinde tek bir yönlendirilmiş çevrimsiz çizge ile orkestre edilmiş, böylece her ürün için aynı anahtar kelimenin dört yönteme değişmeden verilmesi garanti altına alınmıştır.

Sistem, Akakçe üzerinden toplanan 10 kategori grubuna ait 489 gerçek ürün üzerinde kurulmuştur. Değerlendirme, her kategoriden iki farklı markaya ait ikişer ürün seçilerek oluşturulan 20 ürünlük bir alt kümede yürütülmüştür: 20 ürün × 4 yöntem = 80 canlı çalıştırma, 399 arama sonucu ve 46 farklı alan adı. Sonuçların uygunluğu, yöntem tahminleri gizlenmiş bir çalışma kitabı üzerinden elle etiketlenmiş; 193 benzersiz URL için insan etiketi elde edilmiş ve bu etiketler 399 sonucun tamamını kapsamıştır (kapsam oranı %100).

Ölçülen genel doğruluk %76,19'dur. İlk ölçümde asıl bulgu doğruluk sıralamasında değil sınıflandırma davranışındaydı: Selenium + NanoLLM 100 sonucun 100'üne "uygun" demiş, özgüllüğü 0,000 ve dengeli doğruluğu 0,500 çıkmıştır; Agentic Search 99'una "uygun" demiştir. Yürütülen hata analizi bu davranışın nedenini ortaya koymuştur: değerlendirici modele verilen istem ile insan etiketleme kuralı arasında bir tanım uyuşmazlığı vardır — istem kategori sayfalarını uygun sayarken kural saymaz. İstem kuralla hizalanıp aynı sonuçlar yeniden yargılandığında, hiçbir arama tekrarlanmadan ve etiketler değişmeden, Selenium + NanoLLM'in özgüllüğü 0,000'den 0,846'ya, genel doğruluk %76,19'dan %82,46'ya çıkmıştır. Dil modeli kullanmayan kural tabanlı yöntem kontrol grubu olarak hiç değişmemiştir. Kategori kırılımında telefon kategorisi dört yöntem ortalamasında %100 doğrulukla en kolay kategori çıkmış, diğer dokuz grup %73,52 ortalamada kalmıştır.

**Keywords:** e-commerce search relevance, transactional query generation, LLM-as-a-judge, prompt-criterion alignment, agentic search, LangGraph, human relevance judgments, balanced accuracy

---

## ÖZET

**ÜRÜN VERİSİNDEN ANAHTAR KELİME ÜRETİMİ VE ARAMA SONUÇLARININ E-TİCARET UYGUNLUĞUNUN DÖRT YÖNTEMLE KARŞILAŞTIRILMASI**

Atahan Bulut, Ali Rubar Kal
MEF Üniversitesi, Mühendislik Fakültesi, Bilgisayar Mühendisliği Bölümü
Tez Danışmanı: Tuna Çakar
AĞUSTOS, 2026

E-ticaret arama motorlarında bir sorgunun döndürdüğü sayfaların gerçekten satın almaya yönelik olup olmadığını ölçmek, hem sıralama kalitesinin hem de arama motoru optimizasyonu çalışmalarının temel girdisidir. Bu proje, yapılandırılmış ürün kayıtlarından işlemsel niyetli arama sorguları üretmekte ve bu sorguların döndürdüğü sonuçların uygunluğunu dört ayrı yöntemle değerlendirerek yöntemleri aynı veri üzerinde karşılaştırır.

Projenin veri katmanı, Akakçe üzerinden toplanan 10 kategori grubuna ait 489 üründen oluşur; kategori taksonomisi tek bir başvuru dosyasında tanımlanmış ve veri doğrulama bu taksonomiden türetilmiştir. Değerlendirme katmanı, dört yöntemi LangGraph çizgesi üzerinde sırayla çalıştırmakta, her yöntemin çıktısını ortak bir JSON şemasına yazmakta ve bu çıktıları insan etiketleriyle eşleştirerek doğruluk, kesinlik, duyarlılık, özgüllük ve dengeli doğruluk hesaplar.

20 ürünlük değerlendirme alt kümesinde 80 canlı çalıştırma hatasız tamamlanmış, 399 sonuç üretilmiş ve bu sonuçların tamamı 193 benzersiz URL üzerinden elle etiketlenmiştir. Genel doğruluk %76,19 ölçülmüştür. Yöntemlerin üçünün doğruluğu, "her sonuca uygun de" biçimindeki önemsiz sınıflandırıcının doğruluğunu geçememiş veya çok az geçmiştir; bu nedenle raporda doğruluğun yanına özgüllük ve dengeli doğruluk da konulmuştur. Bu davranışın kaynağı hata analiziyle izole edilmiştir: değerlendirici istemi ile etiketleme kuralı aynı ölçütü farklı tanımlamaktaydı. İstem hizalandığında özgüllük 0,000'den 0,846'ya, genel doğruluk %82,46'ya yükselmiş, kontrol grubu olan kural tabanlı yöntem ise hiç değişmemiştir. Danışman geri bildiriminde dile getirilen "tek kategori yeterli değil" eleştirisi ölçümle doğrulanmıştır: telefon kategorisi dört yöntem ortalamasında %100, diğer dokuz kategori %73,52 doğruluk vermiştir.

**Anahtar Kelimeler:** e-ticaret arama uygunluğu, işlemsel sorgu üretimi, dil modeliyle değerlendirme, istem-ölçüt hizalaması, etmen tabanlı arama, LangGraph, insan uygunluk yargıları, dengeli doğruluk

---

## TABLE OF CONTENTS

1. INTRODUCTION
   1.1. Motivation
   1.2. Broad Impact
       1.2.1. Global Impact of the solution
       1.2.2. Economic Impact of the solution
       1.2.3. Environmental Impact of the solution
       1.2.4. Societal Impacts of the solution
       1.2.5. Legal Issues related to the project
2. PROJECT DEFINITION AND PLANNING
   2.1. Project Definition
   2.2. Project Planning
       2.2.1 Aim of the Project
       2.2.2 Project Coverage
       2.2.3 Use Cases
       2.2.4 Success Criteria
       2.2.5 Project Time and Resource Estimation
       2.2.6 Solution Strategies and Applicable Methods
       2.2.7 Risk Analysis
       2.2.8 Tools Needed
3. THEORETICAL BACKGROUND
   3.1. Literature Survey
   3.2. Solution Method: LangGraph Tabanlı Dört Yöntemli Karşılaştırma Hattı
4. ANALYSIS AND MODELLING
   4.1. System Factors
   4.2. How System Works
   4.3. Modelling
       4.3.1. System Architecture
       4.3.2. UML Diagrams
5. DESIGN, IMPLEMENTATION AND TESTING
   5.1. Design
   5.2. Implementation
   5.3. Testing
6. RESULTS
   6.1. Hata analizi: düşük özgüllüğün kaynağı
7. CONCLUSION
   7.1. Life-Long Learning
   7.2. Professional and Ethical Responsibilities of Engineers
   7.3. Contemporary Issues
   7.4. Team Work
APPENDIX A
APPENDIX B
ACKNOWLEDGEMENTS
REFERENCES

---

## LIST OF TABLES

- Tablo 1. Uygunluk değerlendirmesinde kullanılan yöntem ailelerinin yıllara göre gelişimi ve bu projede karşılık gelen yöntem
- Tablo 2. Önergedeki plan ile gerçekleşen iş kırılımı
- Tablo 3. Kategori taksonomisi ve toplanan ürün sayıları
- Tablo 3a. Canlı modelin düşürdüğü ayırt edici nitelikler
- Tablo 4. Güvenilir e-ticaret alan adı tablosunun tür dağılımı
- Tablo 5. Projede kullanılan yazılım araçları ve sürümleri
- Tablo 6. Risk analizi: gerçekleşen ve öngörülen riskler
- Tablo 7. Kaynak kodu ve test kodu büyüklüğü
- Tablo 8. Dört yöntemin genel başarım karşılaştırması
- Tablo 9. Yöntem bazlı karışıklık matrisi
- Tablo 10. Kategori gruplarına göre doğruluk
- Tablo 11. Dondurulmuş telefon deneyi ile çok kategorili deneyin karşılaştırması
- Tablo 12. İstem hizalamasının dört yöntem üzerindeki etkisi

## LIST OF FIGURES

- Şekil 1. Uçtan uca LangGraph çizgesinin düğüm yapısı
- Şekil 2. Dört yöntemli karşılaştırma alt çizgesi
- Şekil 3. Etmen tabanlı arama alt çizgesi
- Şekil 4. Kullanım senaryosu (use case) diyagramı
- Şekil 5. Veri akışı ve bileşen diyagramı
- Şekil 6. Etiketleme ve ölçüm dizisi (sequence) diyagramı
- Şekil 7. Proje Gantt şeması — plan ile gerçekleşenin karşılaştırması

## LIST OF ABBREVIATIONS

| Kısaltma | Açıklama |
|---|---|
| API | Application Programming Interface — Uygulama Programlama Arayüzü |
| CSV | Comma-Separated Values — Virgülle Ayrılmış Değerler |
| DAG | Directed Acyclic Graph — Yönlendirilmiş Çevrimsiz Çizge |
| FN | False Negative — Yanlış Negatif |
| FP | False Positive — Yanlış Pozitif |
| IR | Information Retrieval — Bilgi Erişimi |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model — Büyük Dil Modeli |
| NanoLLM | Bu projede kullanılan küçük ölçekli, ücretsiz katmanlı dil modeli değerlendiricisi |
| SEO | Search Engine Optimization — Arama Motoru Optimizasyonu |
| TN | True Negative — Doğru Negatif |
| TP | True Positive — Doğru Pozitif |
| UML | Unified Modeling Language — Birleşik Modelleme Dili |
| WBS | Work Breakdown Structure — İş Kırılım Yapısı |

---

# 1. INTRODUCTION

Bir kullanıcı e-ticaret araması yaptığında, dönen sayfaların kaçı gerçekten satın almaya yarar? Bu oran iki şeyin doğrudan ölçüsüdür: arama motorunun sıralama kalitesi ve satıcının arama motoru optimizasyonu yatırımı. Bu proje birbirine bağlı iki problemi ele alır. Birincisi, yapılandırılmış ürün verisinden (marka, model, varyant etiketi, kategori) işlemsel niyet taşıyan arama sorgularının otomatik üretilmesidir. İkincisi, bu sorguların döndürdüğü web sonuçlarının e-ticaret uygunluğunun otomatik olarak değerlendirilmesi ve farklı değerlendirme yaklaşımlarının aynı veri üzerinde nesnel biçimde karşılaştırılmasıdır.

Dört yöntem farklı maliyet ve yetenek noktalarını temsil eder. Bu seçim bilinçlidir. Yöntemler şunlardır:

1. Tarayıcı otomasyonuyla toplanan sonuçlar, sabit bir güvenilir alan adı tablosuna göre puanlanır.
2. Aynı sonuçlar küçük bir dil modeliyle değerlendirilir.
3. Ticari bir arama API'sinden gelen sonuçlar aynı dil modeliyle değerlendirilir.
4. Etmen tabanlı yöntem planlama, arama ve değerlendirme adımlarını döngüye sokar.

Dört yöntem de tek bir LangGraph çizgesinde çalışır. Bu çizge, hepsine aynı ürünün ve aynı anahtar kelimenin gitmesini garanti eder.

Projenin ilk aşamasında yalnızca akıllı telefon kategorisi kullanılmıştır. Danışman geri bildirimi üzerine, hattın farklı arama niyetlerine ve farklı ürün yapılarına genellenebildiğini gösterebilmek amacıyla veri kümesi on kategori grubuna genişletilmiş ve karşılaştırma bu genişletilmiş küme üzerinde tekrarlanmıştır. Bu rapor, genişletilmiş deneyin tasarımını, uygulamasını ve ölçülen sonuçlarını sunar.

## 1.1. Motivation

Bu proje üzerinde çalışmanın önemi üç noktada toplanır.

Birincisi, uygunluk ölçümü otomatikleştirilemediği sürece arama kalitesi çalışmaları ölçeklenemez. Bilgi erişimi literatüründe uygunluk yargıları klasik olarak insan değerlendiriciler tarafından üretilir ve bu, Cranfield paradigmasının en pahalı bileşenidir [2]. Son yıllarda büyük dil modellerinin bu yargıları kısmen veya tamamen üstlenip üstlenemeyeceği aktif bir tartışma konusudur [3], [6]. Bu proje, söz konusu tartışmayı Türkçe e-ticaret bağlamında ve küçük, ücretsiz katmanlı modellerle sınayarak somut bir ölçüm sunar.

İkincisi, bir yöntemin "yüksek doğruluk" vermesi ile "gerçekten ayırt etmesi" arasındaki fark, uygulamada sıkça gözden kaçar. Bu projenin ölçümleri, döndürülen sonuçların büyük çoğunluğunun zaten uygun olduğu bir veri kümesinde, hiçbir sonucu reddetmeyen bir sınıflandırıcının bile yüksek doğruluk elde edebildiğini gösterir. Bu nedenle raporda doğruluk tek başına değil, özgüllük ve dengeli doğruluk ile birlikte raporlanmıştır [8].

Üçüncüsü, sonuçlardan doğrudan fayda sağlayacak taraflar bellidir. Ürün kataloğu yöneten satıcılar, hangi anahtar kelime kalıbının hangi tür sayfaları getirdiğini ve hangi otomatik değerlendiricinin manuel kontrol yükünü ne kadar azaltabileceğini görebilir. Fiyat karşılaştırma platformları, katalog eşleştirme kalitesini denetlemek için benzer bir ölçüm hattı kurabilir. Akademik açıdan ise, dört yöntemin aynı ürünler, aynı anahtar kelimeler ve aynı insan etiketleri üzerinde karşılaştırılması, yöntem seçiminin sonuca etkisini yalıtılmış biçimde gösterir.

## 1.2. Broad Impact

Uygunluk değerlendirmesi problemi, bilgi erişimi alanında farklı dönemlerde farklı yöntem aileleriyle ele alınmıştır. Tablo 1, bu gelişimi ve her yöntem ailesinin bu projedeki karşılığını özetler.

**Tablo 1.** Uygunluk değerlendirmesinde kullanılan yöntem ailelerinin gelişimi ve bu projede karşılık gelen yöntem.

| Yıl | Yöntem ailesi | Değerlendirme verisi | Bu projedeki karşılığı |
|---|---|---|---|
| 2000 | İnsan uygunluk yargıları (Cranfield / TREC) [2] | TREC ad hoc koleksiyonları | 193 benzersiz URL için elle üretilen temel doğruluk (ground truth) |
| 2002 | Sorgu niyeti sınıflandırması [1] | AltaVista sorgu kayıtları ve kullanıcı anketi | İşlemsel niyetli anahtar kelime üretimi ve işlemsel amaç ölçütü |
| 2023 | Etmen tabanlı akıl yürütme ve eylem döngüsü [7] | HotpotQA, FEVER, ALFWorld, WebShop | Agentic Search yöntemi (plan → search → evaluate → aggregate) |
| 2023–2025 | Dil modeliyle uygunluk yargısı [3], [4], [5], [6] | Ürün arama ve web arama koleksiyonları | Selenium + NanoLLM ve Tavily + NanoLLM yöntemleri |

### 1.2.1. Global Impact of the solution

Çözümün küresel etkisi, kullanılan yöntemin dile ve pazara görece bağımsız olmasından kaynaklanır. Sistemin girdisi yapılandırılmış ürün kaydı, çıktısı ise ortak bir JSON şemasına yazılan sonuç listesidir; arama sağlayıcısı, değerlendirici model ve güvenilir alan adı tablosu birer yapılandırma öğesidir. Bu ayrıştırma sayesinde aynı hat, farklı bir ülkedeki e-ticaret ekosistemi için yalnızca alan adı tablosu ve kategori taksonomisi değiştirilerek yeniden kullanılabilir. Ayrıca proje, uygunluk değerlendirmesinde küçük ve ücretsiz katmanlı modellerin sınırlarını ölçtüğü için, büyük ticari model bütçesi olmayan araştırmacılar ve küçük işletmeler açısından doğrudan aktarılabilir bir bulgu üretir.

### 1.2.2. Economic Impact of the solution

Ekonomik etki iki yönlüdür. Maliyet tarafında, bu projedeki 80 canlı çalıştırmanın tamamı için kaydedilen tahmini sağlayıcı maliyeti 0,00 USD'dir; çünkü kullanılan OpenRouter modeli ücretsiz katmanda çalışmakta ve Tavily arama maliyeti bu deney için sıfır olarak kaydedilmiştir. Bu, ölçüm hattının ücretsiz katman kotalarıyla kurulabileceğini gösterir; ancak ileriki çalıştırmaların da ücretsiz olacağı anlamına gelmez.

Fayda tarafında, otomatik değerlendirmenin manuel etiketleme yükünü ne kadar azaltabileceği ölçülmüştür. 399 sonucun elle etiketlenmesi iki oturumda tamamlanmıştır. Ölçümlere göre, yöntemlerden yalnızca biri (Tavily + NanoLLM) uygun olmayan sonuçların %39,29'unu reddedebilmiştir; kalan üç yöntem pratikte hiçbir sonucu elemediği için manuel kontrol yükünü anlamlı ölçüde azaltmaz. Bu bulgu, literatürde büyük ölçekli ürün arama değerlendirmesinde insan seviyesine yaklaşan doğruluk bildiren çalışmalarla [5] karşılaştırıldığında, model ölçeğinin ve istem tasarımının belirleyici olduğuna işaret eder.

Projenin doğrudan parasal maliyet kalemleri için: **[EKSİK VERİ: Lütfen donanım (kişisel bilgisayarlar), yazılım lisansı ve insan kaynağı saatlik ücret varsayımlarınızı giriniz; bu değerler proje kayıtlarında yoktur.]**

### 1.2.3. Environmental Impact of the solution

Çevresel etki, hesaplama yoğunluğu üzerinden değerlendirilmelidir. Ölçülen ortalama çalışma süreleri yöntemler arasında beş kattan fazla farklılık gösterir: kural tabanlı yöntem çalıştırma başına ortalama 5,5505 saniye, etmen tabanlı yöntem ise 27,8395 saniye sürer. Bu, en yüksek doğruluğu veren yöntemin aynı zamanda en yüksek hesaplama maliyetini taşımadığını göstermesi bakımından önemlidir: en yüksek doğruluğu veren Tavily + NanoLLM ortalama 12,0785 saniye ile etmen tabanlı yöntemin yaklaşık yarısı kadar sürede tamamlanır. Enerji tüketimi açısından, gereksiz yere daha ağır bir yöntem seçmemek doğrudan bir tasarruf kalemidir.

Veri toplama tarafında da iki önlem alındı. İstekler arasında bekleme konuldu, böylece hedef sitelere gereksiz yük binmedi. Önceki oturumda toplanan ürünler yeniden çekilmedi, devralındı. Toplama üst verisi bunu kaydeder: `carried_over_from_previous_run: 489`, `collected_this_run: 0`.

Sunucu tarafı enerji tüketimi veya karbon eşdeğeri ölçümü yapılmamıştır: **[EKSİK VERİ: Lütfen ölçülmüş enerji tüketimi/karbon değeri varsa giriniz; proje kayıtlarında yoktur.]**

### 1.2.4. Societal Impacts of the solution

Toplumsal etki, tüketicinin arama sonucundan gerçekten ürüne ulaşabilmesiyle ilgilidir. Bu projede uygunluk ölçütü, sayfanın hem sorguda adı geçen ürünün kendisi (belirtilen varyant dâhil) olmasını hem de işlemsel amaç taşımasını gerektirir. Ölçümler, etiketlenmiş 193 URL'nin 53'ünün (%27,5) bu ölçütü karşılamadığını gösterir; yani kullanıcı, döndürülen sonuçların yaklaşık dörtte birinde aradığı ürünün satın alınabilir sayfasına ulaşamaz. Bu oranın kategoriye göre ciddi biçimde değiştiği de ölçülmüştür: uygun sonuç payı telefon ve kitap/müzik/hobi kategorilerinde %95,00 iken, spor/outdoor kategorisinde %56,41'e düşer.

Otomatik değerlendiricilerin toplumsal riski de bu projede somutlaşmıştır. Hiçbir sonucu elemeyen bir değerlendirici, doğruluk metriğinde iyi görünmesine rağmen kullanıcıyı ilgisiz sayfalardan korumaz. Bu nedenle raporda, otomatik değerlendiricilerin yalnızca doğrulukla değil, reddetme kabiliyetiyle birlikte raporlanması gerektiği savunulur.

### 1.2.5. Legal Issues related to the project

Projenin hukuki boyutu esas olarak veri toplama aşamasındadır. Veri, Akakçe üzerinden herkese açık ürün listeleme sayfalarından toplanmıştır. Toplama sırasında aşağıdaki ilkeler uygulanmıştır:

- **Bot korumasının aşılmaması.** Cimri sitesi Cloudflare tabanlı koruma nedeniyle erişilebilir olmamış ve bu koruma aşılmaya çalışılmamıştır; site veri kaynağı olarak tamamen devre dışı bırakılmıştır. Akakçe'de karşılaşılan hız sınırlaması, istekler arası bekleme süresi artırılarak ve toplama işi birden fazla oturuma bölünerek yönetilmiştir. Toplam yedi toplama oturumu kaydedilmiştir.
- **Robots Exclusion Protocol.** robots.txt, IETF tarafından RFC 9309 ile standartlaştırılmıştır [10]. Otomatik istemcilerin bu yönergelere uyması, hukuki zorunluluktan bağımsız olarak yerleşik bir norm olarak kabul edilir [9].
- **Kişisel veri toplanmaması.** Toplanan alanlar yalnızca ürün kimliği, ürün adı, marka, kategori, kaynak bağlantısı ve ürün nitelikleridir; hiçbir kişisel veri toplanmamıştır.
- **Kimlik bilgilerinin depoya girmemesi.** API anahtarları `.env` dosyasında tutulmakta ve sürüm kontrolünde `.gitignore` ile hariç tutulur; depoda yalnızca anahtar içermeyen `.env.example` vardır.
- **Sentetik ve gerçek verinin ayrılması.** Sentetik katalog ile kazınmış veri, üst verideki `acquisition_mode` alanıyla (`synthetic` / `scraped`) ayrılmakta ve bu ayrımı koruyan otomatik testler vardır. Sentetik veri hiçbir koşulda gerçek veri gibi sunulmaz.

Fikri mülkiyet açısından, toplanan veri özgün ifade değil olgusal ürün bilgisidir ve yalnızca akademik değerlendirme amacıyla kullanılmıştır. Araştırma amaçlı web kazımanın hukuki, etik ve kurumsal boyutları literatürde ayrıntılı biçimde tartışılır [9].

---

# 2. PROJECT DEFINITION AND PLANNING

## 2.1. Project Definition

**Kapsam.** Proje, yapılandırılmış ürün kayıtlarından işlemsel niyetli arama sorguları üreten ve bu sorguların döndürdüğü web sonuçlarının e-ticaret uygunluğunu dört farklı yöntemle değerlendirip karşılaştıran uçtan uca bir hat geliştirir. Hat, ham veri toplamadan başlayıp doğrulanmış metrik raporuna kadar olan tüm adımları kapsar.

**İşlevsel gereksinimler.**

1. Sistem, kategori taksonomisine göre e-ticaret sitelerinden ürün verisi toplayabilmelidir; toplanan veri ile sentetik veri üst veride ayrılmalıdır.
2. Sistem, ham ürün verisini temizleyip doğrulayarak kategori profiline uygun bir işlenmiş veri kümesine dönüştürmelidir.
3. Sistem, her ürün için işlemsel niyet taşıyan tek bir anahtar kelime üretmelidir.
4. Sistem, aynı anahtar kelimeyi dört yönteme değiştirmeden vermelidir.
5. Her yöntem, ürün başına en fazla beş arama sonucu döndürmeli ve her sonuç için `predicted_relevant` (boolean) ve `relevance_score` (0–1) üretmelidir.
6. Tüm yöntem çıktıları ortak bir JSON şemasına yazılmalı ve şema doğrulamasından geçmelidir.
7. Sistem, benzersiz URL'leri insan değerlendirmesi için bir Excel çalışma kitabına aktarabilmeli ve doldurulmuş kitabı temel doğruluk dosyasına geri okuyabilmelidir.
8. Sistem, insan etiketleriyle yöntem tahminlerini eşleştirerek doğruluk, kesinlik, duyarlılık, özgüllük ve dengeli doğruluk hesaplamalı; sonuçları hem genel hem kategori bazında raporlamalıdır.

**İşlevsel olmayan gereksinimler.**

1. **Tekrarlanabilirlik.** Bir metrik raporunun hangi sonuç dosyalarından hesaplandığı bir manifest dosyasında dondurulmalı; rapordaki her sayı bu dosyalardan yeniden üretilebilmelidir.
2. **Yansızlık.** İnsan değerlendiriciye yöntem tahminleri gösterilmemelidir.
3. **Karşılaştırılabilirlik.** Bir URL için verilen etiket, o URL'yi döndüren tüm yöntemler için ortak olmalıdır.
4. **Sessiz veri kaybı olmaması.** Eksik etiket, eksik ürün/yöntem kombinasyonu veya çelişkili etiket, sessizce atlanmak yerine işlemi durdurmalıdır.
5. **API'siz test edilebilirlik.** Test paketi ağ erişimi ve API anahtarı gerektirmeden çalışabilmelidir.
6. **Geriye dönük koruma.** Önceki (telefon) deneyinin sonuçları değişmeden yeniden üretilebilmelidir.

## 2.2. Project Planning

**Plan ile gerçekleşenin karşılaştırılması.** Proje planı, 11.07.2026 tarihli önerge formunda sekiz görev olarak verilmiştir. Tablo 2 bu planı, sürüm kontrol geçmişinden çıkarılan gerçekleşen tarihlerle yan yana koyar. Gerçekleşen tarihler, ilgili görevi ilk ve son kez değiştiren işlemlerin (commit) tarihleridir; deponun açılmasından önce tamamlanan iki görev bu şekilde işaretlenmiştir.

**Kapsam değişikliği.** Önerge, sistemi *SEO içerik üretimi ve doğrulaması* olarak tanımlar: başlık uzunluğu, meta açıklama uzunluğu ve anahtar kelime kapsamı gibi ölçütleri kural tabanlı biçimde denetleyen bir doğrulama motoru öngörülmüştür. Geliştirme sırasında araştırma sorusu korunmuş ancak yargının nesnesi değişmiştir: sistem, üretilen içeriğin SEO uyumunu değil, üretilen sorgunun döndürdüğü **arama sonuçlarının e-ticaret uygunluğunu** değerlendirir. Önergedeki asıl soru — nihai kararı belirleyici (deterministik) bir modül mü yoksa dil modeli mi vermelidir — aynen korunmuş, hatta ölçülmüştür (bkz. Bulgu 1 ve Bulgu 6). Bu nedenle önergenin 5. ve 6. görevleri aynı adla değil, aynı işlevle karşılanmıştır. Tablo 2 bu farkı görev görev gösterir.

**Tablo 2.** Önergedeki plan ile gerçekleşen iş kırılımı (kaynak: 11.07.2026 tarihli önerge formu ve sürüm kontrol geçmişi, 69 işlem).

| No | Görev | Sorumlu | Planlanan | Gerçekleşen | Not |
|---|---|---|---|---|---|
| 1 | Problem tanımı ve araştırma sorusu | İkisi | 09.07 – 14.07 | 09.07 – 14.07 | Depo açılmadan önce; önerge 11.07'de teslim edildi |
| 2 | Literatür taraması ve arama stratejisi | İkisi | 15.07 – 23.07 | 15.07 – 22.07 | Depo açılmadan önce; 12 kaynak Bölüm 3.1'de |
| 3 | Ürün veri kümesi ve nitelik şeması | A. R. Kal | 20.07 – 28.07 | 23.07 – 26.07 | Planda "mock" veri kümesi vardı; gerçek kazınmış veri kullanıldı |
| 4 | Nitelik normalizasyon katmanı | A. R. Kal | 27.07 – 04.08 | 23.07 – 26.07 | Kategori duyarlı nitelik doğrulaması olarak gerçeklendi |
| 5 | Kural tabanlı değerlendirme ve kalite kapısı | A. R. Kal | 03.08 – 10.08 | 23.07 – 28.07 | **Kapsam değişti:** SEO doğrulama yerine kural tabanlı uygunluk değerlendirmesi |
| 6 | Dil modeli modülleri | A. Bulut | 08.08 – 14.08 | 23.07 – 28.07 | **Rol değişti:** dil modeli yardımcı değil, ölçülen bir karar vericidir |
| 7 | Uçtan uca hat ve test paketi | İkisi | 13.08 – 17.08 | 28.07 – 06.08 | LangGraph dört yöntemli hat, 399 test |
| 8 | On kategoriye genişletme | İkisi | — | 18.08 – 19.08 | **Planda yok:** ara değerlendirmedeki danışman geri bildirimi üzerine eklendi |
| 9 | Hata analizi: istem–ölçüt hizalaması | A. R. Kal | — | 21.08 | **Planda yok:** raporun ana bulgusu buradan çıktı |
| 10 | Rapor, şekiller ve sunum | A. R. Kal | 16.08 – 20.08 | 21.08 – 23.08 | Üç gün gecikti |

**Şekil 7.** Proje Gantt şeması — plan ile gerçekleşenin karşılaştırması.

Şema, Tablo 2'deki on görevi haftalık ölçekte gösterir. Her görevin iki çubuğu vardır: üstteki açık renkli çubuk önergedeki planı, alttaki koyu çubuk sürüm kontrol geçmişinden okunan gerçekleşen aralığı gösterir. Mor çubuklu iki görev önergede hiç yer almaz.

> Çizim (İngilizce, rapora girecek olan): `reports_multicategory/figures/figure7_gantt_EN.svg`
> Türkçe sürüm: `reports_multicategory/figures/sekil7_gantt_TR.svg`
> Üreteci: `reports_multicategory/figures/make_gantt.py`

**Plandan üç sapma ölçülmüştür.** Birincisi, 3–7. görevler plandan **yaklaşık iki hafta önce** tamamlanmıştır; hattın tamamı 06.08'de çalışır durumdaydı, oysa plan 17.08'i işaret ediyordu. İkincisi, planda hiç bulunmayan iki görev (8 ve 9) eklenmiş ve raporun en anlamlı iki bulgusunu bunlar üretmiştir. Üçüncüsü, rapor yazımı planlanan 20.08 yerine 23.08'de tamamlanmıştır.

Toplam takvim süresi 09.07.2026 – 23.08.2026 arası, yaklaşık **yedi haftadır**. Bunun ilk iki haftası depo açılmadan önceki problem tanımı ve literatür çalışmasıdır; kodlama 23.07'de başlar. Katkı dağılımı sürüm kontrol geçmişine göre Ali Rubar Kal 53 işlem, Atahan Bulut 16 işlemdir.

### 2.2.1 Aim of the Project

Projenin amacı iki adımdır. Önce, ürün verisinden üretilen arama sorgularının getirdiği web sonuçlarının e-ticaret uygunluğunu ölçer. Sonra bu ölçümü dört otomatik değerlendirme yöntemi için tekrarlar. Dört yöntem de aynı veriyi, aynı sorguları ve aynı insan etiketlerini kullanır. Böylece hangi yöntemin ne kadar ayırt edebildiği ve bunun maliyetinin ne olduğu nesnel olarak görülür.

### 2.2.2 Project Coverage

Proje aşağıdaki bileşenleri kapsar:

- **Veri toplama katmanı.** On kategori grubu için Akakçe üzerinden ürün kazıma (BeautifulSoup4 ve Selenium), oturumlar arası devam edebilme ve toplama üst verisi üretimi. Ayrıca çevrimdışı çalışma için sentetik katalog.
- **Veri işleme katmanı.** Kategori profiline göre temizleme, doğrulama ve şema uyumu; doğrulama sorunlarının ayrı bir dosyaya raporlanması.
- **Anahtar kelime üretimi.** Ürün kaydından işlemsel niyetli tek anahtar kelime üretimi; hem canlı LLM hem deterministik mod.
- **Dört değerlendirme yöntemi.** Selenium + Kural Tabanlı, Selenium + NanoLLM, Tavily + NanoLLM, Agentic Search.
- **Orkestrasyon.** LangGraph üzerinde üç çizge: uçtan uca hat, dört yöntemli karşılaştırma alt çizgesi ve etmen tabanlı arama alt çizgesi.
- **İnsan etiketleme döngüsü.** Excel çalışma kitabına dışa aktarım, doldurulmuş kitabın temel doğruluk dosyasına içe aktarımı, belirsiz satırlar için izlenebilir hakem (adjudication) mekanizması.
- **Ölçüm ve raporlama.** Manifest ile dondurulan sonuç kümesi üzerinden genel ve kategori bazlı metrikler; metrik dosyalarından üretilen Markdown rapor.

Kapsam dışında bırakılanlar: sıralama (ranking) kalitesi metrikleri (nDCG vb.), çok koşumlu varyans analizi, çoklu değerlendirici anlaşma katsayısı ve canlı üretim ortamına dağıtım.

### 2.2.3 Use Cases

**Şekil 4.** Kullanım senaryosu (use case) diyagramı.

Diyagramda üç aktör ve sekiz kullanım senaryosu vardır. **Araştırmacı** yedi senaryoyu başlatır: veri toplama, veri temizleme, anahtar kelime üretme, dört yöntemi çalıştırma, etiketleme kitabı üretme, temel doğruluk üretme ve metrik hesaplama. **Değerlendirici** yalnızca bir senaryoda yer alır: URL'leri elle etiketleme. **Danışman** ise yalnızca metrik ve rapor çıktısını görür. Sistemin dışında dört servis bulunur: Akakçe (veri kaynağı), Tavily (arama API'si), OpenRouter (dil modeli) ve Bing (Selenium ile arama). Diyagramdaki iki ilişki önemlidir: etiketleme kitabı üretilirken model tahminleri gizlenir (`«include»`), ve değerlendiricinin belirsiz bıraktığı satır hakem adımına taşınır (`«extend»`).

> Çizim (İngilizce, rapora girecek olan): `reports_multicategory/figures/figure4_use_cases_EN.svg`
> Türkçe sürüm: `reports_multicategory/figures/sekil4_kullanim_senaryolari_TR.svg`
> Üreteci: `reports_multicategory/figures/make_figure4.py`

**Kullanım senaryosu açıklamaları.**

- **UC1 — Ürün verisi topla.** Aktör: Araştırmacı. Ön koşul: kategori taksonomisi tanımlı. Akış: taksonomideki her kategori için arama terimleriyle listeleme sayfaları gezilir, ürün kaydı çıkarılır, üst veri yazılır. Alternatif akış: hedef site hız sınırı uygularsa oturum kaydedilir ve `--resume` ile devam edilir.
- **UC2 — Veriyi temizle ve doğrula.** Kategori profiline göre zorunlu ve isteğe bağlı alanlar denetlenir; sorunlu satırlar ayrı dosyaya yazılır.
- **UC3 — Anahtar kelime üret.** Her ürün için işlemsel niyetli tek anahtar kelime üretilir.
- **UC4 — Dört yöntemi çalıştır.** Aynı anahtar kelime dört yönteme sırayla verilir; her yöntem en fazla beş sonuç döndürür.
- **UC5 — Etiketleme kitabı üret.** Benzersiz URL'ler Excel'e aktarılır; `predicted_relevant` ve `relevance_score` sütunları bilinçli olarak dışarıda bırakılır.
- **UC6 — URL'leri elle etiketle.** Aktör: Değerlendirici. Her URL açılır ve kurala göre true/false seçilir.
- **UC7 — Temel doğruluk üret.** Doldurulmuş kitap(lar) okunur, çelişkiler ve eksikler hata olarak raporlanır, temel doğruluk CSV'si yazılır.
- **UC8 — Metrik ve rapor üret.** Manifest ile dondurulan sonuç dosyaları etiketlerle eşleştirilir; genel ve kategori bazlı metrikler ile Markdown rapor üretilir.

### 2.2.4 Success Criteria

Projenin başarı ölçütleri ve gerçekleşme durumu aşağıdadır. Her ölçütün gerçekleşme değeri, raporun 6. bölümündeki ölçümlerden alınmıştır.

| No | Başarı ölçütü | Hedef | Gerçekleşen | Durum |
|---|---|---|---|---|
| B1 | Kategori genişlemesi | ≥ 10 kategori grubu | 10 grup, 489 ürün | Karşılandı |
| B2 | Kategori başına ürün | ~50 | 9 grup 50; 1 grup 39 | Kısmen karşılandı |
| B3 | Dört yöntemin hatasız canlı çalıştırılması | 80/80 | 80/80, 0 hata | Karşılandı |
| B4 | İnsan etiket kapsamı | ≥ %90 | %100 (399/399) | Karşılandı |
| B5 | Ortak şema doğrulaması | Tüm çıktılar geçerli | 80 dosyanın tamamı geçerli | Karşılandı |
| B6 | Önceki deneyin korunması | Bire bir yeniden üretim | %68,84 değişmeden yeniden üretiliyor | Karşılandı |
| B7 | Otomatik test paketi | Tümü geçmeli | 399 test, 1 atlandı, 0 hata | Karşılandı |
| B8 | En az bir yöntemin önemsiz sınıflandırıcıyı anlamlı biçimde geçmesi | ≥ +5 puan | Tavily + NanoLLM: +10,0 puan | Karşılandı |

B2 ölçütünün kısmen karşılanmasının nedeni ölçülmüş bir olgudur: `saat_moda_taki_ayakkabi` kategorisinde gerçek ilan başlıkları yapılandırılmış teknik özellik yayınlamadığı için hedef ürün sayısına ulaşılamamış ve kategori 39 üründe kalmıştır.

### 2.2.5 Project Time and Resource Estimation

**Takvim süresi.** Proje 09.07.2026'da problem tanımıyla başlamış, 23.08.2026'da rapor ve şekillerin tamamlanmasıyla bitmiştir; toplam takvim süresi yaklaşık **yedi haftadır** (yaklaşık 1,55 ay). Sürüm kontrol geçmişindeki ilk işlem 23.07.2026, son işlem 23.08.2026 tarihlidir; ilk iki hafta depo açılmadan önceki problem tanımı ve literatür çalışmasına aittir.

**Efor tahmini.** Proje kayıtlarında saat bazında zaman çizelgesi tutulmamıştır. Efor, dolaylı göstergelerden tahmin edilebilir: iki kişilik ekip, 69 işlem, 12.632 satır kaynak kodu ve 7.662 satır test kodu üretmiştir. Bu göstergelerden yola çıkarak yaklaşık 2 × 1,55 ≈ **3,10 kişi-ay** üst sınır tahmini yapılabilir; ancak bu tahmin, ekibin bu süre boyunca tam zamanlı çalıştığı varsayımına dayanır ve doğrulanmamıştır.

**[EKSİK VERİ: Lütfen gerçek çalışma saati kaydınız varsa (haftalık saat × hafta × kişi) buraya giriniz; proje kayıtlarında saat bazlı efor verisi yoktur.]**

**Kaynak maliyeti.** Ölçülen sağlayıcı maliyeti, 80 canlı çalıştırmanın tamamı için 0,00 USD'dir (ücretsiz katman modeli ve sıfır olarak kaydedilen arama maliyeti). Donanım olarak yalnızca ekibin kişisel bilgisayarları kullanılmıştır; ek sunucu veya GPU kaynağı kullanılmamıştır. Yazılım yığınının tamamı açık kaynaktır.

**[EKSİK VERİ: Lütfen donanım amortismanı ve insan kaynağı için varsaydığınız birim maliyetleri giriniz; toplam proje maliyeti bu değerler olmadan hesaplanamaz.]**

### 2.2.6 Solution Strategies and Applicable Methods

Uygunluk değerlendirmesi problemi için değerlendirilen alternatif yaklaşımlar ve seçim gerekçeleri aşağıdadır.

**Alt problem 1: Arama sonuçlarının elde edilmesi.**

| Alternatif | Avantaj | Dezavantaj | Karar |
|---|---|---|---|
| Tarayıcı otomasyonu (Selenium) | Gerçek arama motoru sonuç sayfasını olduğu gibi görür; ek API maliyeti yok | Yavaş; CAPTCHA ve bot koruması riski; kırılgan seçiciler | Kullanıldı (iki yöntemde) |
| Arama API'si (Tavily) | Hızlı, kararlı, yapılandırılmış çıktı | Sağlayıcıya bağımlılık; kota sınırı | Kullanıldı (bir yöntemde) |
| Doğrudan HTML kazıma | Bağımlılık az | Arama motorları bot korumasıyla engelliyor | Kullanılmadı |

İki farklı toplama yolunun aynı deneyde tutulması bilinçlidir: bu sayede "değerlendirici farkı" ile "toplama yolu farkı" ayrıştırılabilir. Selenium + NanoLLM ile Tavily + NanoLLM aynı değerlendiriciyi kullandığı için aralarındaki fark doğrudan toplama yoluna atfedilebilir.

**Alt problem 2: Uygunluk kararının verilmesi.**

| Alternatif | Avantaj | Dezavantaj | Karar |
|---|---|---|---|
| Kural tabanlı alan adı puanlaması | Deterministik, çok hızlı, açıklanabilir | Tabloda olmayan alan adlarını kör noktaya sokar | Kullanıldı (temel çizgi) |
| Küçük ölçekli dil modeli (NanoLLM) | Sayfa başlığı ve özetini yorumlayabilir; ücretsiz katman | Kararsız; aşırı hoşgörülü olabilir | Kullanıldı |
| Etmen tabanlı akıl yürütme (ReAct benzeri) [7] | Sorguyu planlayıp birden fazla arama yapabilir | En yüksek gecikme; hata yayılımı | Kullanıldı |
| Denetimli sınıflandırıcı eğitimi | Veriye özel yüksek başarım | Yeterli etiketli veri yok (193 etiket) | Kullanılmadı |
| Büyük ticari dil modeli | Literatürde insan seviyesine yakın sonuç [5] | Maliyet ve kota | Kullanılmadı |

**Alt problem 3: Temel doğruluğun üretilmesi.** Literatürde uygunluk yargılarının tamamen dil modeline bırakılması tartışmalıdır [3]. Bu projede, karşılaştırılan yöntemlerin kendisi dil modeli tabanlı olduğu için temel doğruluğun dil modeliyle üretilmesi döngüsel bir yanlılık yaratacaktı. Bu nedenle etiketler tamamen insan tarafından, yöntem tahminleri gizlenmiş bir çalışma kitabı üzerinden üretilmiştir.

**Alt problem 4: Orkestrasyon.** Dört yöntemin ayrı betiklerle çalıştırılması, aynı anahtar kelimenin dört yönteme gittiğini garanti etmez. Bu nedenle LangGraph tabanlı tek bir durum çizgesi tercih edilmiş; anahtar kelime tek bir düğümde üretilip ortak duruma yazılmış ve dört yöntem düğümü bu ortak durumdan okumuştur.

### 2.2.7 Risk Analysis

**Tablo 6.** Risk analizi: gerçekleşen ve öngörülen riskler.

| No | Risk | Olasılık | Etki | Önlem / Gerçekleşme durumu |
|---|---|---|---|---|
| R1 | Hedef sitenin bot koruması veri toplamayı engeller | Yüksek | Yüksek | **Gerçekleşti.** Cimri, Cloudflare koruması nedeniyle erişilemedi. Koruma aşılmaya çalışılmadı; kaynak devre dışı bırakılıp Akakçe'ye yoğunlaşıldı. |
| R2 | Hız sınırlaması toplamayı yavaşlatır | Yüksek | Orta | **Gerçekleşti.** Akakçe hız sınırı uyguladı. İstekler arası bekleme artırıldı, toplama yedi oturuma bölündü, `--resume` ile ilerleme korundu. |
| R3 | Kategoriye özgü alanlar gerçek ilanlarda bulunmaz | Orta | Orta | **Gerçekleşti.** Moda ilanları yapılandırılmış özellik yayınlamıyor. Şema, yalnızca `variant_label` zorunlu olacak biçimde gevşetildi; kategoriye özgü alanlar isteğe bağlı yapıldı. İlgili kategori 39 üründe kaldı. |
| R4 | Sağlayıcı günlük kotası deneyi yarıda keser | Yüksek | Yüksek | **Gerçekleşti ve önlem yetersiz kaldı.** Anahtar rotasyonu eklendi (`OPENROUTER_API_KEY_2`); kotası dolan anahtar kenara ayrılıp diğerine geçiliyor. Ancak ölçüm, iki anahtarın da aynı OpenRouter hesabına ait olduğunu ve ücretsiz katman limitinin anahtar başına değil **hesap başına** uygulandığını göstermiştir (her iki anahtar için `limit=50`, `kalan=0`, aynı `user_id`). Rotasyon bu nedenle ek günlük kapasite sağlamaz. Deney, kotanın gün içinde tükenmesine karşı oturumlara bölünerek yürütülmüştür. |
| R5 | Aynı sayfanın değerlendiriciye iki kez gitmesi | Orta | Orta | **Gerçekleşti.** Dışa aktarım ham URL üzerinden, metrikler normalize URL üzerinden tekilleştiriyordu; sondaki eğik çizgi farkı bir sayfayı iki kez etiketletti. İki taraf ortak normalizasyona geçirildi; uyumlu tekrarlar tek kayda indiriliyor, çelişkili tekrarlar içe aktarımı durduruyor. |
| R6 | Değerlendiricinin belirsiz bıraktığı satırlar ölçümü bloke eder | Orta | Orta | **Gerçekleşti.** Beş satır belirsiz bırakıldı. Çalışma kitabı değiştirilmeden, ayrı bir hakem dosyasında kural referansıyla çözüldü; her hakem kararı temel doğruluk dosyasının not alanına gerekçesiyle yazıldı. |
| R7 | Refaktör önceki deneyin sonuçlarını bozar | Orta | Yüksek | **Önlendi.** Genişletme öncesinde mevcut davranışı bire bir kaydeden karakterizasyon testleri yazıldı; dondurulmuş telefon deneyi hâlâ %68,84 ile yeniden üretiliyor. |
| R8 | Değerlendirici modelin tüm sonuçlara "uygun" demesi | Orta | Yüksek | **Gerçekleşti ve ölçüldü.** Selenium + NanoLLM 100/100 sonuca uygun dedi. Bu, doğruluk yanına özgüllük, dengeli doğruluk ve önemsiz sınıflandırıcı taban çizgisi eklenerek raporda görünür kılındı. |
| R9 | Etiket yanlılığının ölçülememesi | Orta | Orta | **Kısmen açık.** Etiketleme iki ekip üyesi arasında bölünmüştür (birinci oturum 134 satır, ikinci oturum 61 satır). Ancak ikinci çalışma kitabı, birincinin kapsadığı URL'leri tasarım gereği dışladığı için iki kümenin kesişimi sıfırdır; hiçbir URL iki kez etiketlenmemiştir. Bu nedenle değerlendiriciler arası anlaşma katsayısı hesaplanamamıştır. Sınırlılık olarak raporlanmıştır. |
| R10 | Tek koşum nedeniyle varyansın bilinmemesi | Yüksek | Orta | **Açık.** Ürün/yöntem başına tek koşum yapılmıştır; güven aralığı verilemez. Sınırlılık olarak raporlanmıştır. |

### 2.2.8 Tools Needed

**Tablo 5.** Projede kullanılan yazılım araçları ve sürümleri (kaynak: `requirements.txt` ve çalıştırma ortamı).

| Araç | Sürüm | Kullanım amacı |
|---|---|---|
| Python | 3.14.3 | Tüm hattın uygulama dili |
| Selenium | 4.46.0 | Tarayıcı otomasyonu ile arama sonucu toplama |
| BeautifulSoup4 | ≥ 4.12.0 | HTML ayrıştırma (ürün kazıma) |
| LangGraph | ≥ 0.2.0 | Durum çizgesi tabanlı orkestrasyon |
| Pydantic | ≥ 2.7.0 | Yapılandırılmış çıktı şeması doğrulaması |
| pandas | 3.0.3 | Tablo işleme ve kural tabanlı puanlama |
| NumPy | 2.5.1 | Sayısal işlemler |
| openpyxl | ≥ 3.1.0 | Etiketleme çalışma kitabının yazılması ve okunması |
| requests | ≥ 2.32.0 | HTTP istekleri (API çağrıları) |
| python-dotenv | ≥ 1.0.0 | Ortam değişkeni yönetimi (API anahtarları) |
| pytest | ≥ 8.2.0 | Test altyapısı (paket `unittest` ile de çalıştırılabilir) |
| Git / GitHub | — | Sürüm kontrolü ve iş birliği |
| Microsoft Excel | — | İnsan etiketleme arayüzü |

Dış servisler: OpenRouter (dil modeli sağlayıcısı, `google/gemma-4-26b-a4b-it:free` modeli), Tavily (arama API'si), Akakçe (ürün veri kaynağı), Bing/Google (Selenium üzerinden arama).

Donanım: ekibin kişisel bilgisayarları. Ek sunucu, GPU veya bulut kaynağı kullanılmamıştır.

---

# 3. THEORETICAL BACKGROUND

Bu bölümde, projenin dayandığı problem tanımı ve ilgili literatür sunulmakta, ardından geliştirilen çözüm yöntemi ayrıntılı anlatılır.

**Problem tanımı.** Süreç bir ürün kaydıyla başlar. Bu kayıttan işlemsel niyetli bir anahtar kelime üretilir. Anahtar kelime bir arama yöntemine verilir; yöntem en fazla beş sonuç döndürür ve her sonuç için "uygun" veya "uygun değil" der. Aynı sonuç için insan değerlendirici de bir karar verir; bu karar gerçek etiket sayılır.

Problem şudur: dört yöntemin verdiği kararlar ile insanın verdiği kararlar ne kadar örtüşüyor? Bu ölçüm dört yöntem için de aynı ürünler, aynı anahtar kelimeler ve aynı insan etiketleri üzerinde yapılır. Böylece yöntemler arasındaki fark yöntemin kendisinden gelir, ölçüldükleri veriden değil.

Burada kritik bir nokta var: insan etiketi **sonucun** özelliğidir, yöntemin değil. Bir URL'yi birden fazla yöntem döndürebilir. O URL için verilen tek etiket, onu döndüren bütün yöntemler için geçerlidir. Bu tasarım kararı, yöntemlerin farklı etiket kümeleri üzerinde ölçülmesini ve dolayısıyla karşılaştırmanın anlamsızlaşmasını engeller.

## 3.1. Literature Survey

**Uygunluk yargıları ve değerlendirme koleksiyonları.** Bilgi erişimi değerlendirmesinin yerleşik çerçevesi olan Cranfield paradigması üç bileşene dayanır: belge kümesi, bilgi ihtiyacı ifadeleri ve uygunluk yargıları. Voorhees, TREC ad hoc görevinde farklı değerlendiricilerin ürettiği uygunluk yargı kümelerinin sistem sıralamalarını nasıl etkilediğini incelemiş ve bireysel yargılar arasında belirgin farklar bulunmasına rağmen sistemlerin göreli sıralamasının kararlı kaldığını göstermiştir [2]. Bu bulgu, bu projenin tasarımı açısından önemlidir: az sayıda değerlendirici tarafından üretilen etiketler mutlak doğruluk değerlerini kaydırabilir, ancak yöntemlerin birbirine göre sıralamasının bundan görece az etkilenmesi beklenir.

**Sorgu niyeti.** Broder, web aramalarını kullanıcının amacına göre gezinme (navigational), bilgi edinme (informational) ve işlem yapma (transactional) olarak sınıflandıran taksonomiyi önermiştir [1]. Bu projede üretilen anahtar kelimeler bilinçli olarak işlemsel niyet taşıyacak biçimde tasarlanmıştır (ürün adı, varyant ve "fiyat" kalıbı); uygunluk ölçütünün ikinci koşulu olan "işlemsel amaç" da doğrudan bu taksonomiden türetilmiştir.

**Dil modelleriyle uygunluk yargısı.** Büyük dil modellerinin uygunluk yargılarını üstlenip üstlenemeyeceği güncel bir tartışma alanıdır. Faggioli ve arkadaşları, tamamen manuelden tamamen otomatiğe uzanan bir "insan–makine iş birliği spektrumu" tanımlamış ve dil modeli yargılarının eğitimli insan değerlendiricilerle korelasyonunu inceleyen bir pilot çalışma sunmuştur [3]. Ürün araması özelinde Mehrdad ve arkadaşları, dil modellerinin e-ticaret verisiyle ince ayarlanarak uygunluk etiketlemesinin ölçeklenebileceğini ve altın standart etiketlere yaklaşan doğruluklara ulaşılabileceğini bildirmiştir [6]. Sachdev ve arkadaşları, düşünce zinciri istemi, bağlam içi öğrenme ve erişimle desteklenmiş üretim gibi teknikleri sorgu–ürün uygunluk etiketlemesine uygulamıştır [4]. Hosseini ve arkadaşları ise çok kipli dil modelleriyle, sorguya özel açıklama yönergeleri üreterek büyük ölçekli ürün erişimi değerlendirmesi yapmış; 20.000 örnek üzerinde insan değerlendirici doğruluğuna yakın sonuçlar elde etmiştir [5].

Bu projenin bulguları söz konusu literatürle önemli bir noktada ayrışır. Yukarıdaki çalışmalar genellikle büyük veya ince ayarlanmış modellerle ve özenle tasarlanmış istemlerle çalışır. Bu projede kullanılan ücretsiz katmanlı küçük model, ölçülen koşullarda uygun olmayan sonuçların hiçbirini reddedememiştir (özgüllük 0,00). Bu, dil modeliyle değerlendirmenin model ölçeğine ve istem tasarımına güçlü biçimde bağımlı olduğunu gösterir.

**Etmen tabanlı akıl yürütme.** Yao ve arkadaşlarının önerdiği ReAct çerçevesi, akıl yürütme izleri ile eylemleri iç içe üreterek modelin dış kaynaklarla etkileşime girmesini ve plan güncellemesi yapmasını sağlar [7]. Bu projedeki Agentic Search yöntemi, aynı fikri planlama–arama–değerlendirme–toplama döngüsü olarak somutlaştırır. Ancak ölçümler, bu yöntemin en yüksek gecikmeyi (ortalama 27,8395 saniye) getirmesine rağmen ayırt etme kabiliyetinde anlamlı bir kazanım sağlamadığını (özgüllük 0,0435) gösterir.

**Dengesiz sınıf dağılımında metrik seçimi.** Doğruluk, sınıf dağılımı dengesiz olduğunda yanıltıcıdır; çoğunluk sınıfını tahmin eden önemsiz bir sınıflandırıcı yüksek doğruluk elde edebilir. Brodersen ve arkadaşları, yanlı bir sınıflandırıcının dengesiz veri kümesinde iyimser bir doğruluk tahmini ürettiğini göstermiş ve dengeli doğruluğu (duyarlılık ile özgüllüğün ortalaması) bu soruna karşı bir ölçüt olarak önermiştir [8]. Bu projenin veri kümesinde etiketlenmiş URL'lerin %72,16'sı uygundur; dolayısıyla dengeli doğruluk ve özgüllük raporlaması metodolojik bir zorunluluktur.

**Web kazımanın etik ve hukuki çerçevesi.** Brown ve arkadaşları, araştırma amaçlı web kazımayı hukuki, etik, kurumsal ve bilimsel yönleriyle ele aldı [9]. Vardıkları sonuç şudur: robots.txt yönergelerine uymak hukuki bir zorunluluk değildir, ama yerleşik bir normdur. robots.txt, 2022 yılında IETF tarafından RFC 9309 ile resmî bir standarda kavuşturulmuştur [10]. Bu projede bot korumaları aşılmamış, hız sınırlarına uyulmuş ve kişisel veri toplanmamıştır.

## 3.2. Solution Method: LangGraph Tabanlı Dört Yöntemli Karşılaştırma Hattı

Geliştirilen çözüm, altı aşamalı bir hattır.

**Aşama 1 — Kategori taksonomisi.** On kategori grubu tek bir başvuru dosyasında (`data/reference/product_categories.csv`) tanımlanmıştır. Her satır; kategori grubu anahtarını, Türkçe görünen adı, ürün kimliği ön ekini, hedef ürün sayısını, zorunlu ve isteğe bağlı nitelikleri ve sayısal nitelik aralıklarını taşır. Bu dosya, hem kazıyıcının hem doğrulayıcının hem de raporlayıcının tek doğruluk kaynağıdır.

**Tablo 3.** Kategori taksonomisi ve toplanan ürün sayıları.

| Kategori grubu | Görünen ad | Ön ek | Hedef | Toplanan | İsteğe bağlı nitelikler |
|---|---|---|---|---|---|
| elektronik_cep_telefonu | Elektronik, Cep Telefonu | ELK | 50 | 50 | storage_gb, ram_gb |
| ev_yasam_ofis_kirtasiye | Ev, Yaşam, Ofis, Kırtasiye | EVY | 50 | 50 | room_or_use |
| anne_bebek_oyuncak | Anne, Bebek, Oyuncak | ABO | 50 | 50 | age_range |
| saat_moda_taki_ayakkabi | Saat, Moda, Takı, Ayakkabı | SMT | 50 | 39 | size_label, color |
| kitap_muzik_hobi | Kitap, Müzik, Hobi | KMH | 50 | 50 | creator |
| spor_outdoor | Spor, Outdoor | SPO | 50 | 50 | discipline |
| saglik_bakim_kozmetik | Sağlık, Bakım, Kozmetik | SBK | 50 | 50 | volume_ml |
| oto_bahce_yapi_market | Oto, Bahçe, Yapı Market | OBY | 50 | 50 | power_or_volume |
| petshop | Petshop | PET | 50 | 50 | animal_type, weight_kg |
| supermarket | Süpermarket | SPM | 50 | 50 | net_weight_g |
| **Toplam** | | | **500** | **489** | |

Şema tasarımında kritik karar, kategoriye özgü alanların isteğe bağlı bırakılmasıdır. Yalnızca `variant_label` alanı zorunludur. Bunun gerekçesi ölçülmüş bir olgudur: gerçek ilan başlıkları, özellikle moda kategorisinde, yapılandırılmış teknik özellik içermez. Alanları zorunlu kılmak, veri kaybına veya sentetik doldurmaya yol açacaktı.

**Aşama 2 — Veri toplama.** Ürünler Akakçe üzerinden BeautifulSoup4 ve Selenium ile toplanmıştır. Toplama üst verisi `acquisition_mode: scraped` değerini taşır. Çevrimdışı çalışma ve test için ayrıca sentetik bir katalog bulunmakta ve bu katalog `acquisition_mode: synthetic` ile açıkça işaretlenir. Toplanan veri kümesi 489 üründen ve 156 farklı markadan oluşur.

**Aşama 3 — Veri işleme ve doğrulama.** İşleme adımı profil tabanlıdır: her kategori grubunun kendi zorunlu alan tanımı vardır ve telefon profili, önceki deneyin davranışını bire bir koruyacak şekilde bırakılmıştır. İşlenmiş veri kümesi 489 ürün içermekte ve doğrulama sorunu sayısı 0'dır.

**Aşama 4 — Anahtar kelime üretimi.** Her ürün için işlemsel niyetli tek bir anahtar kelime üretilir (örnek: `ELK001` → "iPhone 17 256 GB Siyah fiyat"). Üreteç iki modda çalışabilir. Bu deneydeki 489 anahtar kelime **deterministik (fake) modda** üretilmiştir (`execution_mode: fake`, `model: deterministic-fake-keyword-generator`, `prompt_version: keyword-generation-v1`, çalışma süresi 0,01 s). Canlı LLM yolunun çalıştığı ayrı bir duman testiyle (smoke test) kanıtlanmıştır: 3 ürün, OpenRouter sağlayıcısı, `google/gemma-4-26b-a4b-it:free` modeli, 19,03 saniye, 0,00 USD. Bu ayrım raporda bilinçli olarak belirtilir; anahtar kelimelerin canlı model tarafından üretildiğini iddia etmek yanlış olurdu.

Deterministik üreteç `{marka} {model} {varyant} fiyat` kalıbını kurar; uydurma veri üretmez, gerçek ürün kaydının alanlarını birleştirir. Canlı istemci ise aynı alanları (`product_name`, `brand`, `model`, `category_group`, `variant_label`, `attributes`) modele göndermekte ve istemde açıkça "markayı, ürün adını, `variant_label` alanındaki ayırt edici varyantı ve *fiyat* gibi bir satın alma niyetini içer" talimatını verir. Yani iki yol **aynı girdiyi** görmekte, yalnızca kelimeyi kuran taraf değişir.

**Bu tercihin isabeti ölçülmüştür.** Değerlendirmeye giren 20 ürünün tamamı için anahtar kelimeler canlı modelle yeniden üretilmiş ve deterministik listeyle karşılaştırılmıştır (Tablo 3a). Yedi ürün birebir aynı çıkmış, 13 üründe fark oluşmuştur. Farkların bir bölümü biçimseldir ("fiyat" yerine "fiyatı", "Energy Plus" yerine "Energy+"), ancak yedi üründe canlı model ürün adındaki **ayırt edici niteliği düşürmüştür**.

**Tablo 3a.** Canlı modelin düşürdüğü ayırt edici nitelikler (20 üründen 7'si).

| Ürün | Deterministik | Canlı model | Düşen bilgi | Korunum |
|---|---|---|---|---|
| OBY002 | Castrol Magnatec 10W-40 A3/B4 4 lt Motor Yağı | Castrol Magnatec 10 W Motor Yağı | viskozite sınıfı, spesifikasyon, hacim | %44 |
| EVY001 | Tefal Ingenio Ceramic Renew 11 Parça Büyük Tencere Seti | Tefal Ingenio Ceramic Renew 11 Parça | ürün tipi | %67 |
| ELK001 | iPhone 17 256 GB Siyah | Apple iPhone 17 256 GB | renk | %80 |
| PET002 | Enjoy Tavuklu 15 kg Yetişkin Kedi Maması | Enjoy 15 kg Yetişkin Kedi Maması | tat | %86 |
| KMH002 | CA Games Mona Lisa Puzzle 1000 Parça 7022 | CA Games Mona Lisa Puzzle 1000 Parça | model kodu | %88 |
| PET001 | Pro Plan Somonlu 10 kg Kısırlaştırılmış Kedi Maması | Pro Plan 10 kg Kısırlaştırılmış Kedi Maması | tat | %89 |
| OBY001 | Shell Helix Ultra Professional AG 5W-30 5 lt | Shell Helix Ultra Professional AG 5 W-30 5 lt | viskozite yazımı | %91 |

Ürün adındaki bilginin ortalama korunumu deterministik üreteçte **%100,0** (20/20 üründe tam), canlı modelde **%92,2**'dir. Bu fark yöntemsel olarak önemlidir: uygunluk ölçütünün birinci koşulu sayfanın "anahtar kelimede belirtilen varyantı" taşımasıdır. Anahtar kelime varyantı adlandırmayı bıraktığında bu koşul uygulanamaz hale gelir. Dolayısıyla deterministik üreteç bu deney için yalnızca pratik bir kolaylık değil, **ölçüt bütünlüğü açısından daha doğru** seçimdir; ayrıca girdiyi sabitleyerek deneyin tekrarlanabilirliğini garanti eder.

**Aşama 5 — Dört değerlendirme yöntemi.**

1. **Selenium + Kural Tabanlı.** Tarayıcı otomasyonuyla toplanan her sonucun alan adı, 44 kayıtlık güvenilir e-ticaret alan adı tablosunda aranır. Bulunursa tablodaki `relevance_score` değeri atanır; bulunmazsa 0,0 atanır. `RELEVANCE_THRESHOLD = 0.60` eşiğini geçen sonuçlar uygun sayılır. Yöntem tamamen deterministiktir ve dil modeli kullanmaz.

**Tablo 4.** Güvenilir e-ticaret alan adı tablosunun tür dağılımı (44 kayıt, puan aralığı 0,85–1,00).

| Alan adı türü | Kayıt sayısı |
|---|---|
| retailer (perakendeci) | 29 |
| marketplace (pazar yeri) | 7 |
| manufacturer_store (üretici mağazası) | 5 |
| price_comparison (fiyat karşılaştırma) | 2 |
| classified_marketplace (ilan sitesi) | 1 |

2. **Selenium + NanoLLM.** Aynı Selenium toplama yolu kullanılır; ancak uygunluk kararı, sonuç başlığı ve özeti üzerinden küçük ölçekli dil modeliyle verilir.
3. **Tavily + NanoLLM.** Sonuçlar Tavily arama API'sinden alınır; değerlendirme yine aynı dil modeliyle yapılır. Bu yöntem ile bir öncekinin karşılaştırılması, toplama yolunun etkisini yalıtır.
4. **Agentic Search.** Planlama, arama, değerlendirme ve toplama düğümlerinden oluşan bir alt çizge çalıştırılır; planlayıcı düğüm birden fazla arama sorgusu üretebilir.

**Aşama 6 — Etiketleme ve ölçüm.** Yöntemlerin döndürdüğü benzersiz URL'ler Excel çalışma kitabına aktarılır. Çalışma kitabı `predicted_relevant` ve `relevance_score` sütunlarını bilinçli olarak içermez; bu, temel doğruluğun herhangi bir yönteme doğru kaymasını önlemek içindir. Doldurulmuş kitap(lar) geri okunarak temel doğruluk CSV'si üretilir ve metrikler hesaplanır.

**Uygunluk kuralı.** Değerlendiriciye çalışma kitabının yönerge sayfasında şu kural verildi.

Bir sonuç uygundur, ancak iki koşul birlikte sağlanırsa:

1. Sayfa, anahtar kelimede adı geçen ürünün kendisidir. Anahtar kelime bir varyant belirtiyorsa (depolama, hacim, ağırlık, beden, sürüm), sayfa o varyantı taşır.
2. Sayfa işlemsel amaç taşır: perakendeci ürün sayfası, pazar yeri ilanı, seri ilan veya fiyat karşılaştırma sayfası.

Bir sonuç uygun değildir, şu durumlarda:

- farklı bir ürün veya farklı bir varyanttır,
- ürünün kendisi değil aksesuarıdır,
- haber, blog, inceleme veya forum sayfasıdır,
- ürüne ulaşmayan bir kategori veya arama sayfasıdır.

**Stokta olmamak, bir sayfayı uygunsuz yapmaz.**

---

# 4. ANALYSIS AND MODELLING

## 4.1. System Factors

Sistemin davranışını etkileyen faktörler dört başlıkta toplanır.

**Dış servis faktörleri.** Sistem üç dış servise bağımlıdır: arama motoru (Selenium üzerinden), Tavily arama API'si ve OpenRouter dil modeli API'si. Bu servislerin kota sınırları, gecikmeleri ve bot korumaları sistemin çalışabilirliğini doğrudan etkiler. Ölçülen etkiler: OpenRouter ücretsiz katmanı **hesap başına** günde 50 model isteği ile sınırlıdır. Uygulamaya birden fazla anahtarı sırayla deneyen bir rotasyon mekanizması eklenmiş olsa da, ölçüm bu mekanizmanın ek kapasite sağlamadığını göstermiştir: eldeki iki anahtar aynı hesaba ait olduğu için ikisi de aynı 50 isteklik günlük havuzu paylaşır. Gerçek kapasite artışı ancak ayrı bir hesap veya ücretli katman ile mümkündür. Veri toplama tarafında Akakçe hız sınırlaması uygulamış, Cimri ise Cloudflare koruması nedeniyle tamamen erişilemez olmuştur.

**Veri faktörleri.** Sonuçların uygunluk oranı kategoriye göre belirgin biçimde değişir (%56,41 ile %95,00 arası). Bu değişkenlik, doğruluk metriğinin kategoriler arası karşılaştırmada tek başına yorumlanmasını engeller. Ayrıca ürün adlarının yapısı kategoriye göre farklılaşır: telefon adları model ve depolama bilgisini içerirken, moda ürün adları çoğunlukla üretici kodu taşır.

**Değerlendirici faktörleri.** Dil modeli tabanlı değerlendiricilerin karar eşiği istem tasarımına ve model ölçeğine bağlıdır. Ölçümler, kullanılan modelin uygunluk yönünde güçlü bir eğilim taşıdığını gösterir.

**İnsan faktörleri.** Temel doğruluk iki değerlendirici tarafından üretilmiştir; etiketler iki oturuma bölünmüş ve her oturumu bir ekip üyesi tamamlamıştır. İki oturumun URL kümeleri kesişmediği için değerlendiriciler arası tutarlılık ölçülemez. Voorhees'in gösterdiği gibi, değerlendirici değişkenliği mutlak değerleri kaydırabilir ancak sistemlerin göreli sıralamasını görece az etkiler [2].

## 4.2. How System Works

Sistem, tek bir ürün için aşağıdaki adımları izler:

1. **Ürün yükleme.** İşlenmiş veri kümesinden ürün kimliğine göre kayıt okunur. Kayıt bulunamazsa hat, hata mesajıyla durur.
2. **Anahtar kelime üretimi.** Ürün adı, markası ve varyant etiketinden işlemsel niyetli tek anahtar kelime üretilir ve ortak duruma yazılır.
3. **Yöntemlerin çalıştırılması.** Ortak durumdaki anahtar kelime dört yöntem düğümüne sırayla verilir. Her düğüm en fazla beş sonuç döndürür ve her sonuç için alan adı, URL, başlık, özet, `predicted_relevant` ve `relevance_score` alanlarını doldurur. Bir yöntem hata verirse hata kaydedilir ve hat diğer yöntemlerle devam eder.
4. **Sonuçların sıralanması ve toplanması.** Yöntem çıktıları birleştirilir.
5. **Kalıcılaştırma.** Her yöntem/ürün çifti için, çalıştırma modunu ve zaman damgasını taşıyan ayrı bir JSON dosyası yazılır.
6. **Doğrulama.** Yazılan her dosya ortak şemaya göre doğrulanır: zorunlu alanların varlığı, URL'nin `http://` veya `https://` ile başlaması, `predicted_relevant` alanının boolean olması ve `relevance_score` alanının 0–1 aralığında bulunması denetlenir.

Ölçüm tarafında akış şöyledir: benzersiz URL'ler çalışma kitabına aktarılır, elle etiketlenir, temel doğruluğa geri okunur; hangi sonuç dosyalarının rapora gireceği bir manifest dosyasında dondurulur; metrikler bu manifest üzerinden hesaplanır.

## 4.3. Modelling

### 4.3.1. System Architecture

Sistem üç katmandan oluşur.

**Şekil 5.** Veri akışı ve bileşen diyagramı.

Diyagram üç katmanı yukarıdan aşağıya gösterir. **Veri katmanında** kategori taksonomisi kazıyıcıyı yönlendirir; kazıyıcı Akakçe'den 489 ürün toplar; veri işleme ve kalite kontrolü bu ürünleri temizler; anahtar kelime üreteci her ürün için bir sorgu yazar. **Değerlendirme katmanında** toplu koşum sürücüsü dört yöntemi aynı anahtar kelimeyle çalıştırır; raporda kullanılan 80 koşum bu yoldan üretilmiştir. Aynı dört yöntem, LangGraph çizgesi üzerinden de çalıştırılabilir (Şekil 1). Her yöntemin kendi arama kaynağı ve kendi karar vericisi vardır, ama hepsi çıktısını ortak JSON şemasına yazar ve doğrulamadan geçer. **Ölçüm katmanında** benzersiz URL'ler Excel'e aktarılır, elle etiketlenir, hakem dosyasıyla birlikte temel doğruluğa dönüşür; manifest hangi sonuç dosyalarının rapora gireceğini dondurur; metrikler ve rapor bu dondurulmuş kümeden üretilir.

> Çizim (İngilizce, rapora girecek olan): `reports_multicategory/figures/figure5_system_architecture_EN.svg`
> Türkçe sürüm: `reports_multicategory/figures/sekil5_sistem_mimarisi_TR.svg`
> Üreteci: `reports_multicategory/figures/make_figure5.py`

Mimarinin iki tasarım ilkesi vardır. Birincisi, **ortak şema**: dört yöntem birbirinden tamamen bağımsız çalışsa da hepsi aynı JSON şemasına yazmak zorundadır; bu, metrik katmanının yöntemden habersiz kalmasını sağlar. İkincisi, **dondurulmuş manifest**: bir rapor, hangi sonuç dosyalarından hesaplandığını açıkça listeleyen bir manifest üzerinden üretilir; hattın yeniden çalıştırılması yeni dosyalar üretse bile rapor hesaplandığı koşuma bağlı kalır.

### 4.3.2. UML Diagrams

**Şekil 1.** Uçtan uca LangGraph çizgesinin düğüm yapısı (aktivite diyagramı karşılığı).

Çizge altı düğümden oluşur ve düz bir sıra izler: `load_product` → `generate_keyword` → `compare_methods` → `rank_results` → `aggregate` → `persist_output`. İlk düğüm ürün kaydını okur; kayıt bulunamazsa hat hata mesajıyla durur. İkinci düğüm anahtar kelimeyi üretip ortak duruma yazar. Üçüncü düğüm dört yöntemi çalıştıran alt çizgedir (Şekil 2). Son düğüm her yöntem/ürün çifti için bir JSON dosyası yazar.

```
  START
    │
    ▼
┌──────────────┐   ürün kaydı bulunamazsa → hata mesajıyla durur
│ load_product │
└──────┬───────┘
       ▼
┌──────────────────┐
│ generate_keyword │  işlemsel niyetli tek anahtar kelime → ortak durum
└──────┬───────────┘
       ▼
┌──────────────────┐
│ compare_methods  │  (alt çizge — bkz. Şekil 2)
└──────┬───────────┘
       ▼
┌──────────────┐
│ rank_results │
└──────┬───────┘
       ▼
┌──────────────┐
│  aggregate   │
└──────┬───────┘
       ▼
┌────────────────┐
│ persist_output │  yöntem/ürün başına bir JSON dosyası
└──────┬─────────┘
       ▼
      END
```

**Şekil 2.** Dört yöntemli karşılaştırma alt çizgesi.

Alt çizge önce `input` düğümünde ortak durumdan ürünü ve anahtar kelimeyi okur. Ardından dört yöntemi tek sıra hâlinde çalıştırır: `selenium_rule_based` → `selenium_nano_llm` → `tavily_llm` → `agentic_search`. Son düğüm `result_aggregation` çıktıları birleştirir. Bir yöntem hata verirse hata kaydedilir ve akış bir sonraki yöntemle devam eder; tek bir yöntemin başarısızlığı diğer üçünü durdurmaz.

```
  START
    │
    ▼
┌───────┐
│ input │  ortak durumdan ürün ve anahtar kelimeyi okur
└───┬───┘
    ▼
┌─────────────────────┐
│ selenium_rule_based │  bir yöntem hata verirse hata kaydedilir,
└───┬─────────────────┘  akış bir sonraki yöntemle devam eder
    ▼
┌───────────────────┐
│ selenium_nano_llm │
└───┬───────────────┘
    ▼
┌────────────┐
│ tavily_llm │
└───┬────────┘
    ▼
┌────────────────┐
│ agentic_search │
└───┬────────────┘
    ▼
┌────────────────────┐
│ result_aggregation │
└───┬────────────────┘
    ▼
   END
```

Yöntemlerin sıralı (paralel değil) çalıştırılması bilinçli bir karardır: dış servis kotalarının eşzamanlı isteklerle hızla tükenmesini ve hedef sitelere ani yük binmesini önler.

**Şekil 3.** Etmen tabanlı arama alt çizgesi.

Bu alt çizgede dört düğüm vardır: `plan` → `search` → `evaluate` → `aggregate`. `plan` düğümü dil modelini kullanarak bir veya birden fazla arama sorgusu üretir. `search` düğümü bu sorguları çalıştırır; bir arama hata verirse hata kaydedilir ve akış sürer. `evaluate` düğümü her sonuç için uygunluk kararı verir.

```
  START ──▶ plan ──▶ search ──▶ evaluate ──▶ aggregate ──▶ END
             │         │           │
             │         │           └─ her sonuç için uygunluk kararı
             │         └─ arama hatası kaydedilir, akış sürer
             └─ bir veya birden fazla arama sorgusu üretir
```

**Şekil 6.** Etiketleme ve ölçüm dizisi (sequence) diyagramı.

Diyagram altı katılımcı arasındaki mesaj sırasını gösterir. Araştırmacı dışa aktarım aracını çağırır; araç, model tahminleri gizlenmiş bir Excel dosyası üretir. Değerlendirici 193 URL'yi elle etiketler. Araştırmacı içe aktarım aracını çağırır; araç, doldurulmuş kitabı ve hakem dosyasını okuyarak 193 kayıtlık temel doğruluğu yazar. Sonra manifest üreteci 80 sonuç dosyasını dondurur ve ürün/yöntem ızgarasında delik olmadığını denetler. Son olarak metrik araçları genel ve kategori bazlı raporları üretir.

> Çizim (İngilizce, rapora girecek olan): `reports_multicategory/figures/figure6_labeling_sequence_EN.svg`
> Türkçe sürüm: `reports_multicategory/figures/sekil6_etiketleme_dizisi_TR.svg`
> Üreteci: `reports_multicategory/figures/make_figure6.py`

---

# 5. DESIGN, IMPLEMENTATION AND TESTING

## 5.1. Design

**Modül tasarımı.** Kaynak kod, sorumluluk sınırlarına göre ayrılmıştır. Veri katmanı modülleri (`category_taxonomy.py`, `product_scraper.py`, `product_catalog.py`, `data_processor.py`, `quality_check.py`) değerlendirme yöntemlerinden habersizdir. Yöntem modülleri (`rule_based_evaluator.py`, `nano_llm_evaluator.py`, `tavily_client.py`, `agentic_search.py`) birbirinden habersizdir. Ölçüm modülleri (`ground_truth.py`, `metrics.py`, `result_validator.py`, `category_metrics.py`) yalnızca ortak JSON şemasını bilir.

**Veri sözleşmeleri.** Sistemde üç kritik sözleşme vardır:

1. **Sonuç şeması.** Her sonuç dosyası şu alanları taşımak zorundadır: `product_id`, `keyword`, `method`, `execution_mode`, `provider`, `model`, `prompt_version`, `runtime_seconds`, `estimated_cost_usd`, `results`. Her sonuç öğesi ise `domain`, `url`, `title`, `snippet`, `predicted_relevant`, `relevance_score` alanlarını taşır. `execution_mode` yalnızca `live` veya `fake` olabilir; `method` yalnızca dört tanımlı yöntemden biri olabilir.
2. **Temel doğruluk şeması.** `product_id, keyword, method, domain, url, human_relevant, notes`. `method` alanının boş bırakılması bilinçlidir: boş değer, etiketin o URL'yi döndüren tüm yöntemler için ortak olduğu anlamına gelir.
3. **Manifest şeması.** `report_scope`, `evaluation_subset_file`, `ground_truth_file`, `selected_result_files`.

**Hata tasarımı.** Sistem, sessiz veri kaybı yerine gürültülü başarısızlık ilkesini benimser. Eksik etiket, çelişkili etiket, ürün/yöntem ızgarasında delik, geçersiz sonuç dosyası ve eşleşmeyen hakem kaydı durumlarının her biri işlemi durdurur ve sorunu satır numarasıyla raporlar.

**URL kimliği.** Aynı sayfanın farklı yazımları (sondaki eğik çizgi, ana bilgisayar adının büyük/küçük harfi) tek bir kimliğe indirgenir; sorgu dizesi ise korunur, çünkü pazar yerlerinde varyant filtreleri sorgu dizesinde taşınır. Bu normalizasyon hem dışa aktarım hem içe aktarım hem de metrik eşleştirme tarafında ortak kullanılır.

**Hakem (adjudication) tasarımı.** Değerlendiricinin bilinçli olarak belirsiz bıraktığı satırlar, çalışma kitabı değiştirilerek değil, ayrı bir CSV dosyasında çözülür. Bu dosya `product_id, url, resolved_label, rule, adjudicated_by` sütunlarını taşır. Tasarım üç güvence sunar:

1. Bir hakem kaydı yalnızca değerlendiricinin okunamaz bıraktığı satıra uygulanır. Değerlendiricinin verdiği bir cevabı asla değiştiremez.
2. Hiçbir satırla eşleşmeyen hakem kaydı içe aktarımı durdurur.
3. Her hakem kararı, ham cevabı ve dayandığı kuralı temel doğruluk dosyasının `notes` alanına yazar.

Böylece bir denetçi bu satırları dışlayıp metrikleri yeniden hesaplayabilir.

## 5.2. Implementation

**Tablo 7.** Kaynak kodu ve test kodu büyüklüğü (satır sayısı).

| Katman | Dosya sayısı | Satır sayısı |
|---|---|---|
| Kaynak kodu (`src/`) | 35 | 12.632 |
| Test kodu (`tests/`) | 24 | 7.662 |
| **Toplam** | **59** | **20.294** |

En büyük modüller: `product_scraper.py` (1.443), `langgraph_flow.py` (1.131), `data_processor.py` (779), `quality_check.py` (640), `keyword_generator.py` (630), `import_label_workbook.py` (513), `multicategory_report.py` (481), `category_metrics.py` (464), `export_label_workbook.py` (418), `selenium_collector.py` (404).

**Uygulama ayrıntıları.**

*Kazıyıcı.* `product_scraper.py`, kategori başına arama terimleri üzerinden listeleme sayfalarını gezer. Bir listeleme sayfası yaklaşık 32 ürün taşıdığından, 50 ürünlük hedefe ulaşmak için kategori başına en az iki çalışan arama terimi gerekir. Kazıyıcı, oturum kesintilerinde ilerlemeyi kaydetmekte ve `--resume` bayrağıyla devam edebilir; toplam yedi toplama oturumu kaydedilmiştir.

*Profil tabanlı işleme.* `data_processor.py` ve `quality_check.py`, kategori grubuna göre farklı zorunlu alan kümeleri uygular. Telefon profili, önceki deneyin davranışını bire bir koruyacak biçimde bırakılmıştır.

*Kural tabanlı değerlendirici.* `rule_based_evaluator.py`, alan adını 44 kayıtlık tabloda arar; bulamazsa 0,0 puan verir. `RELEVANCE_THRESHOLD = 0.60` sabiti eşiği belirler. Modül ayrıca tablodaki puanların 0–1 aralığında ve sayısal olduğunu doğrulamakta, geçersiz puan bulursa açık bir hata mesajı üretir.

*API anahtarı rotasyonu.* OpenRouter ücretsiz katmanı **hesap başına** günde 50 model isteği ile sınırlıdır. Uygulama, `OPENROUTER_API_KEY_2` biçiminde numaralandırılmış ek anahtarları desteklemekte; günlük kotası dolan anahtarı kenara ayırıp bir sonrakine geçmekte, denenmemiş anahtar kalmadığında ise geri çekilme (backoff) uygular. Mekanizmanın dayandığı varsayım her anahtarın kendi kotasına sahip olmasıdır; bu varsayım yalnızca anahtarlar **farklı hesaplara** ait olduğunda geçerlidir. Bu projede kullanılan iki anahtar aynı hesaba ait olduğundan rotasyon ek günlük kapasite sağlamamıştır.

*Manifest üreteci.* `build_manifest.py`, sonuç dizinindeki her dosyayı doğrular, yalnızca `live` modundaki koşumları dikkate alır ve her (ürün, yöntem) çifti için dosya adındaki zaman damgasına göre en yeni koşumu seçer. Yöntem adları alt çizgi içerdiğinden (`selenium_rule_based`), zaman damgası dosya adını parçalara ayırmak yerine doğrudan düzenli ifadeyle eşleştirilir. Üreteç, ürün/yöntem ızgarasında bir delik bulursa manifest yazmayı reddeder.

*Kategori bazlı metrikler.* `category_metrics.py`, her (yöntem, kategori) çifti için karışıklık matrisi ve türetilmiş metrikleri hesaplar. Tanımsız oranlar (örneğin hiç uygunsuz etiket yoksa özgüllük) sıfır olarak değil, eksik olarak raporlanır.

## 5.3. Testing

**Test stratejisi.** Test paketi üç amaca hizmet eder:

1. **Karakterizasyon (kilit) testleri:** kategori genişletmesi öncesinde mevcut davranışı bire bir kaydeder.
2. **Birim testleri:** yeni bileşenlerin sözleşmelerini sabitler.
3. **Gerileme testleri:** bulunan her hata için bir tane yazılır.

**Test paketinin ölçülen durumu.** Test paketi 24 dosya ve 7.500'ü aşkın satırdan oluşur. Çalıştırma sonucu: **399 test, 1 atlandı, 0 hata, 0 başarısızlık**; toplam çalışma süresi yaklaşık 1,2 saniyedir. Test paketi ağ erişimi veya API anahtarı gerektirmez; dış servisler sahte (fake) uygulamalarla değiştirilmiştir. Bu, testlerin kota tüketmeden ve internet bağlantısı olmadan çalışabilmesini sağlar.

**Karakterizasyon testleri.** Kategori genişletmesine başlamadan önce üç sözleşme testi dosyası yazıldı. Bu dosyalar mevcut telefon hattının davranışını kaydeder:

- **Veri sözleşmesi:** şema sabitleri, temizleme davranışı, doğrulama hata sözlüğü.
- **Yöntem sözleşmesi:** alan adı tablosu, puanlama, anahtar kelime üretimi, URL yardımcıları, API anahtarı rotasyonu.
- **Orkestrasyon sözleşmesi:** çizge topolojisi, JSON sözleşmesi.

Bu testler sayesinde genişletmeden sonra telefon deneyinin %68,84 doğruluğunun bozulmadığı doğrulanabilir.

**Testle yakalanan hatalar.** Geliştirme sırasında altı gerçek hata bulunmuş ve her biri için kilit testi eklenmiştir:

1. **URL tekilleştirme uyuşmazlığı.** Dışa aktarım modülü ham URL üzerinden, metrik modülü ise normalize URL üzerinden tekilleştirme yapmaktaydı. Sondaki eğik çizgi farkı, aynı sayfanın değerlendiriciye iki kez gitmesine ve iki etiketin metrik katmanında çakışmasına yol açtı. Düzeltme: her iki taraf ortak normalizasyon fonksiyonunu kullanacak biçimde değiştirildi; uyumlu tekrarlar tek kayda indiriliyor, çelişkili tekrarlar içe aktarımı durduruyor. Bu davranış beş ayrı testle sabitlendi.
2. **Etiketsiz yöntemin rapordan düşmesi.** Kategori bazlı metrik modülünde, sonuçlarının hiçbiri etiketlenmemiş bir yöntem rapordan tamamen kayboluyordu; bu, dört yöntemli bir karşılaştırmanın sessizce üç yöntemli hale gelmesi anlamına gelirdi. Düzeltme: böyle bir yöntem, puanlanamadığı açıkça belirtilerek raporda tutulur.
3. **Sınırsız geri çekilme (backoff) süresi.** OpenRouter istemcisi, hız sınırı yanıtındaki `Retry-After` başlığını üst sınır olmaksızın uyguluyordu. Günlük kotası dolan bir hesapta bu başlık gece yarısını işaret edebildiği için toplu çalıştırma tek bir üründe saatlerce askıda kalıyordu; ölçülen iki vakada 29 dakika ve bir saatten fazla. Düzeltme: bekleme 60 saniyeyle sınırlandırıldı. Gerekçe ölçülebilir: günlük limit zaten anahtarı kenara ayırıp rotasyonla çözülüyor, dakikalık limit ise saniyeler içinde açılıyor, dolayısıyla uzun bekleme hiçbir şey kazandırmadan işi durduruyor. Beş test bu davranışı sabitledi.
4. **Göreli manifest yolunun kabul edilmemesi.** Kategori raporu, manifest yolu komut satırından göreli verildiğinde çöküyordu; yalnızca mutlak varsayılan yol denenmiş olduğu için hata görünmemişti. Düzeltme: yol önce çözümleniyor.
5. **Yüzde kodlamalı URL'lerin ayrı sayfa sayılması.** URL normalizasyonu `%3A` gibi yüzde kodlamalarını çözmediği için aynı sayfanın iki yazımı iki ayrı URL gibi görünüyordu. Hatayı, etiketleme çalışma kitabında aynı sayfayı iki kez gören değerlendirici fark etti. Düzeltme sonrası benzersiz URL sayısı 194'ten 193'e indi; hiçbir metrik değişmedi, çünkü iki yazım da aynı etiketi taşıyordu.
6. **Üretilen raporun elde kalması.** `reports_multicategory/` altındaki Markdown raporlar üretilir ama depoya işlenir. Yüzde kodlama düzeltmesinden sonra tüm JSON metrik dosyaları yeniden hesaplandı, ancak İngilizce karşılaştırma raporu 194 değerinde kaldı ve bir commit boyunca tüm denetimlerden geçti: tutarlılık denetleyicisi Türkçe raporu ve JSON dosyalarını okuyor, üretilen İngilizce raporu okumuyordu. Düzeltme: her Markdown rapor, işlenmiş metriklerden yeniden üretilip bayt bayt karşılaştırılıyor.

Altısının ortak yanı, hiçbirinin yanlış sonuç üretmemesi, hepsinin **sessiz veri kaybına veya işin durmasına** yol açmasıdır. Bu, ölçüm altyapısının kendisinin de en az ölçülen sistem kadar test edilmesi gerektiğini gösterir.

**Test kapsamı örnekleri.** Etiketleme döngüsü için yazılan testler şu davranışları sabitler:

- Belirsiz cevap (`true?`) asla etiket sayılmaz.
- Hakem kaydı, değerlendiricinin verdiği cevabı değiştiremez.
- Eşleşmeyen hakem kaydı içe aktarımı durdurur.
- Büyük/küçük harf ve boşluk farkları eşleşmeyi bozmaz.

Manifest üreteci için yazılan testler ise şunları kapsar:

- En yeni koşum seçilir.
- `fake` modundaki koşumlar dondurulmaz.
- Izgarada delik varsa üretim reddedilir.
- Alt küme dışı ürün bulunursa hata verilir.

---

# 6. RESULTS

Bu bölümdeki tüm değerler, `reports_multicategory/multicategory_evaluation_metrics.json` ve `reports_multicategory/multicategory_category_metrics.json` dosyalarından alınmıştır. Bu dosyalar, `data/evaluation/final_evaluation_manifest_multicategory.json` manifestinde dondurulan 80 sonuç dosyası ile `data/labels/multicategory_ground_truth.csv` temel doğruluk dosyasından hesaplanmıştır.

**Deney protokolü.**

| Öğe | Değer |
|---|---|
| Ürün sayısı | 20 (10 kategori × 2 ürün, 20 farklı marka) |
| Yöntem sayısı | 4 |
| Canlı çalıştırma sayısı | 80 (hata yok) |
| Toplam arama sonucu | 399 |
| Benzersiz URL | 195 |
| Benzersiz alan adı | 46 |
| Elle etiketlenen benzersiz URL | 193 |
| Etiket kapsamı | %100 (399/399) |
| Uygun etiket / uygunsuz etiket | 140 / 53 |
| Hakem kararıyla çözülen satır | 5 |
| Tekilleştirme ile birleştirilen satır | 2 |

Etiketleme iki oturumda yürütülmüştür: birinci oturumda 134 satır, ikinci oturumda 61 satır. Her oturumu bir ekip üyesi tamamlamıştır. İkinci çalışma kitabı, birincisinde etiketlenen URL'leri tasarım gereği dışlar; bu nedenle iki değerlendiricinin etiket kümeleri kesişmemekte ve aralarındaki anlaşma ölçülemez (bkz. Ölçüm sınırlılıkları).

**Genel sonuç.** 399 etiketli sonucun 304'ünde yöntem tahmini insan etiketiyle örtüşmüştür; genel doğruluk **%76,19**'dur. Toplam karışıklık sayıları: TP = 289, TN = 15, FP = 86, FN = 9.

**Tablo 8.** Dört yöntemin genel başarım karşılaştırması.

| Yöntem | Sonuç | Doğruluk | "Hep uygun" taban çizgisi | Dengeli doğruluk | Kesinlik | Duyarlılık | Özgüllük | Ort. süre (s) | Maliyet (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Tavily + NanoLLM | 100 | **0,8200** | 0,7200 | **0,6895** | 0,8068 | 0,9861 | **0,3929** | 12,0785 | 0,00 |
| Agentic Search | 100 | 0,7800 | 0,7700 | 0,5218 | 0,7778 | 1,0000 | 0,0435 | 27,8395 | 0,00 |
| Selenium + NanoLLM | 100 | 0,7400 | 0,7400 | 0,5000 | 0,7400 | 1,0000 | 0,0000 | 14,1995 | 0,00 |
| Selenium + Kural Tabanlı | 99 | 0,7071 | 0,7576 | 0,5091 | 0,7614 | 0,8933 | 0,1250 | **5,5505** | 0,00 |

"Hep uygun" taban çizgisi sütunu, o yöntemin döndürdüğü her sonuca "uygun" cevabı veren önemsiz bir sınıflandırıcının elde edeceği doğruluğu gösterir. Bu değer varsayımsal değildir; yöntemin kendi sonuç kümesindeki uygun etiket oranıdır.

**Bulgu 1: Üç yöntem önemsiz sınıflandırıcıyı geçemez.** Taban çizgisini geçen yöntemler ve marjları: Tavily + NanoLLM **+10,0 puan**, Agentic Search **+1,0 puan**. Selenium + NanoLLM taban çizgisine tam olarak eşittir (0,7400 = 0,7400). Selenium + Kural Tabanlı ise taban çizgisinin **5,05 puan altındadır** (0,7071 < 0,7576).

**Bulgu 2: Dil modeli tabanlı değerlendiriciler neredeyse hiçbir sonucu reddetmez.** Yöntemlerin "uygun" deme oranları ve uygunsuz sonuçları reddetme oranları:

- Selenium + NanoLLM: sonuçların **%100,00**'üne uygun demiştir; uygunsuz sonuçların **%0,00**'ını reddetmiştir (26 uygunsuz sonuçtan 0'ı).
- Agentic Search: sonuçların %99,00'una uygun demiştir; uygunsuz sonuçların %4,35'ini reddetmiştir (23'ten 1'i).
- Selenium + Kural Tabanlı: sonuçların %88,89'una uygun demiştir; uygunsuz sonuçların %12,50'sini reddetmiştir (24'ten 3'ü).
- Tavily + NanoLLM: sonuçların %88,00'ına uygun demiştir; uygunsuz sonuçların %39,29'unu reddetmiştir (28'den 11'i).

Selenium + NanoLLM'in dengeli doğruluğu 0,5000'dir; bu, ikili sınıflandırmada tesadüf düzeyidir [8].

**Tablo 9.** Yöntem bazlı karışıklık matrisi.

| Yöntem | TP | TN | FP | FN | Etiketli sonuç |
|---|---:|---:|---:|---:|---:|
| Tavily + NanoLLM | 71 | 11 | 17 | 1 | 100 |
| Agentic Search | 77 | 1 | 22 | 0 | 100 |
| Selenium + NanoLLM | 74 | 0 | 26 | 0 | 100 |
| Selenium + Kural Tabanlı | 67 | 3 | 21 | 8 | 99 |

**Bulgu 3: Kural tabanlı yöntemin yanlış negatifleri tablodan kaynaklanır.** Kural tabanlı yöntem, dört yöntem arasında yanlış negatiflerin neredeyse tamamını üretir (9 yanlış negatifin 8'i). Bunun nedeni yapısaldır: yöntem, güvenilir alan adı tablosunda bulunmayan bir alan adına 0,0 puan verir. Tabloda bulunmayan üretici mağazaları ve niş perakendeciler, gerçekte uygun ürün sayfaları sunmalarına rağmen eşiği geçemez. Sonuçlarda görülen 46 farklı alan adının yalnızca 44'ü tabloda tanımlıdır ve sonuçlarda `tefal.com.tr` (7 sonuç) ve `efsanekamp.com` (7 sonuç) gibi uzun kuyruk alan adları belirgin biçimde yer alır.

**Bulgu 4: Toplama yolu, değerlendiriciden daha belirleyicidir.** Selenium + NanoLLM ile Tavily + NanoLLM aynı değerlendirici modeli kullanır; aralarındaki tek fark sonuçların nereden geldiğidir. Doğruluk farkı 8 puandır (0,7400'e karşı 0,8200) ve özgüllük farkı 0,3929'dur. Bu, ölçülen koşullarda arama sonuçlarının kalitesinin, değerlendirici modelin kendisinden daha belirleyici olduğunu gösterir.

**Tablo 10.** Kategori gruplarına göre doğruluk ve uygun sonuç payı.

| Kategori grubu | Etiketli | Uygun payı | Tavily+NanoLLM | Agentic | Selenium+NanoLLM | Kural Tabanlı |
|---|---:|---:|---:|---:|---:|---:|
| anne_bebek_oyuncak | 40 | 0,8250 | 0,800 | 0,900 | 0,800 | 0,700 |
| elektronik_cep_telefonu | 40 | 0,9500 | 1,000 | 1,000 | 1,000 | 1,000 |
| ev_yasam_ofis_kirtasiye | 40 | 0,7750 | 0,700 | 0,900 | 0,800 | 0,800 |
| kitap_muzik_hobi | 40 | 0,9500 | 1,000 | 1,000 | 1,000 | 0,800 |
| oto_bahce_yapi_market | 40 | 0,7500 | 0,900 | 0,800 | 0,700 | 0,700 |
| petshop | 40 | 0,6500 | 0,800 | 0,600 | 0,600 | 0,600 |
| saat_moda_taki_ayakkabi | 40 | 0,7000 | 0,600 | 0,700 | 0,800 | 0,500 |
| saglik_bakim_kozmetik | 40 | 0,6750 | 0,900 | 0,600 | 0,600 | 0,600 |
| spor_outdoor | 39 | 0,5641 | 0,800 | 0,600 | 0,400 | 0,667 |
| supermarket | 40 | 0,6250 | 0,700 | 0,700 | 0,700 | 0,700 |

**Bulgu 5: Telefon kategorisi setteki en kolay kategoridir.** Dört yöntem ortalaması alındığında telefon kategorisi **%100,00**, diğer dokuz kategori grubu ise **%73,52** doğruluk verir. Bu, danışman geri bildiriminde dile getirilen kaygının ölçümle doğrulanması anlamına gelir: yalnızca telefon kategorisiyle yürütülen bir değerlendirme, hattın diğer kategorilerdeki başarımını olduğundan iyi gösterir. Uygun sonuç payı da kategoriye göre %56,41 ile %95,00 arasında değişir; bu değişkenlik, doğruluğun kategoriler arası doğrudan karşılaştırılmasını engeller.

**Tablo 11.** Dondurulmuş telefon deneyi ile çok kategorili deneyin karşılaştırması.

| Deney | Ürün | Çalıştırma | Etiketli sonuç | Genel doğruluk |
|---|---:|---:|---:|---:|
| Yalnızca telefon (dondurulmuş) | 10 | 40 | 199 | %68,84 |
| Çok kategorili | 20 | 80 | 399 | %76,19 |

Yöntem bazında dondurulmuş telefon deneyinin doğrulukları: Tavily + NanoLLM %74,00; Selenium + Kural Tabanlı %69,39; Agentic Search %66,00; Selenium + NanoLLM %66,00. İki deney farklı ürünler, farklı anahtar kelimeler ve farklı etiketler kullandığından genel değerler doğrudan karşılaştırılabilir değildir. Buradaki tek çıkarım, her iki deneyde de Tavily + NanoLLM'in en yüksek doğruluğu vermesi ve önceki deneyin sonuçlarının genişletme sonrasında değişmeden yeniden üretilebilmesidir.

## 6.1. Hata analizi: düşük özgüllüğün kaynağı

Yukarıdaki Bulgu 2, LLM tabanlı değerlendiricilerin uygun olmayan sonuçları neredeyse hiç reddetmediğini gösterir. Bu, ilk okunuşta bir **model yetersizliği** olarak yorumlanabilir. Ancak ölçüm hattı incelendiğinde, değerlendirici modele sorulan sorunun insan değerlendiriciye sorulan soruyla aynı olmadığı görülmüştür.

**Tespit edilen uyuşmazlık.** Değerlendirici modelin sistem istemi (`relevance-v1`, 24.07.2026) şunu diyor:

> *"Relevant means product, **category**, marketplace, retailer, or price-comparison intent."*

Buna karşılık insan değerlendiriciye verilen kural (18.08.2026) şunu diyor:

> *"IRRELEVANT when: it is a **category** or search page that does not reach the product."*

İstem kategori sayfalarını uygun sayarken kural saymaz. İki metin farklı zamanlarda, birbirinden bağımsız yazılmış ve hiç karşılaştırılmamıştır. Bu, yazılım mühendisliğinde *specification drift* olarak bilinen hata sınıfının bir örneğidir: aynı ölçüt iki ayrı yerde tutulduğunda ayrı ayrı evrilir.

Bu uyuşmazlık nedeniyle mevcut sayılar tek başına iki olasılığı ayırt edemez: model yargılayamıyor mu, yoksa modele yanlış soru mu soruluyor?

**Deney tasarımı.** Sorunun cevabı kontrollü bir yeniden değerlendirmeyle aranmıştır. Etiketleme kuralının birebir karşılığı olan yeni bir istem (`relevance-v2-aligned`) yazılmış ve depoda saklı sonuçlar bu istemle yeniden yargılanmıştır. Tasarımın dört kısıtı vardır:

1. **Yeni arama yapılmamıştır.** Kayıtlı başlık, özet ve URL'ler kullanılmıştır; dolayısıyla 193 insan etiketinin tamamı geçerliliğini korur. Doğrulanmıştır: 80 dosyanın 80'inde sonuç içeriği birebir aynıdır.
2. **Kural tabanlı yöntem kontrol grubudur.** LLM kullanmadığı için istemden etkilenmez; 20 dosyası bit düzeyinde değiştirilmeden taşınmıştır.
3. **İstem bir kez yazılıp bir kez çalıştırılmıştır.** Sonuca bakıp istemi iyileştirmek, istemi test kümesine uydurmak (overfitting) olurdu ve karşılaştırmayı geçersiz kılardı.
4. **Model, sıcaklık ve şema değişmemiştir.** Tek değişken istemdir.

**Tablo 12.** İstem hizalamasının etkisi (aynı 399 sonuç, aynı 193 etiket).

| Yöntem | Doğruluk | Özgüllük | Dengeli doğruluk | "Uygun" deme oranı |
|---|---|---|---|---|
| Agentic Search | 0,780 → **0,890** | 0,043 → **0,783** | 0,522 → 0,852 | 0,990 → 0,760 |
| Selenium + NanoLLM | 0,740 → **0,850** | 0,000 → **0,846** | 0,500 → 0,849 | 1,000 → 0,670 |
| Tavily + NanoLLM | 0,820 → **0,850** | 0,393 → **0,750** | 0,690 → 0,820 | 0,880 → 0,710 |
| Selenium + Kural Tabanlı *(kontrol)* | 0,707 → 0,707 | 0,125 → 0,125 | 0,509 → 0,509 | 0,889 → 0,889 |

Genel doğruluk **%76,19 → %82,46** olmuştur. Karışıklık sayıları yöntem bazında şöyle değişmiştir:

| Yöntem | TP | TN | FP | FN |
|---|---|---|---|---|
| Selenium + NanoLLM | 74 → 63 | **0 → 22** | 26 → 4 | 0 → 11 |
| Agentic Search | 77 → 71 | 1 → 18 | 22 → 5 | 0 → 6 |
| Tavily + NanoLLM | 71 → 64 | 11 → 21 | 17 → 7 | 1 → 8 |
| Selenium + Kural Tabanlı | 67 → 67 | 3 → 3 | 21 → 21 | 8 → 8 |

**Bulgu 6: Düşük özgüllük model yetersizliğinden değil, ölçüt uyuşmazlığından kaynaklanır.** Selenium + NanoLLM'in özgüllüğü 0,000'den 0,846'ya çıkmıştır; yöntem, uygun olmayan 26 sonuçtan hiçbirini reddedemezken 22'sini reddeder hale gelmiştir. Kontrol grubu olan kural tabanlı yöntemin hiç değişmemesi, farkın tek kaynağının istem olduğunu doğrular.

Önemsiz sınıflandırıcı taban çizgisiyle fark da buna paralel değişmiştir: Selenium + NanoLLM +0,0 puandan +11,0 puana, Agentic Search +1,0 puandan +12,0 puana, Tavily + NanoLLM +10,0 puandan +13,0 puana çıkmıştır. Yani ilk ölçümde iki yöntem "her şeye uygun de" davranışından ayırt edilemezken, hizalama sonrasında üçü de taban çizgisini net biçimde geçer.

**Bulgu 7: Hizalama farkın tamamını açıklamaz.** Yanlış negatifler sıfıra yakın değerlerden 6-11 aralığına yükselmiştir; yeni istem bazı geçerli ürün sayfalarını da reddeder. Üç yöntemde toplam **73 karar değişmiş**, bunların **49'u insan etiketiyle uyumlu, 24'ü uyumsuz** yöne gitmiştir (Selenium + NanoLLM 22/11, Agentic Search 17/6, Tavily + NanoLLM 10/7). Yani hizalama net kazanç sağlamakta, ancak modelin her yeni reddi doğru değildir. Doğru yöne dönen kararlar beklendiği gibi kategori sayfalarında yoğunlaşır (`hepsiburada.com/molfix/bebek-bezi-c-60001048?filtreler=beden:6`, `tefal.com.tr/tava-ve-tencereler/ingenio/`, `akakce.com/kedi-mamasi/pro-plan.html`). Dolayısıyla küçük modelin kendi sınırları hizalama sonrasında da görünür kalır.

**Bu bulgunun anlamı.** Sonuç, "küçük dil modelleri uygunluk yargısı veremez" biçiminde bir model değerlendirmesi değildir. Ölçülen şey, **değerlendirme tanımının hassasiyetidir**: aynı model, ölçütü tarif eden metindeki tek bir kelime yüzünden ya tesadüf düzeyinde ya da kullanılabilir bir sınıflandırıcı gibi davranır. Bu, dil modeliyle uygunluk yargısı üzerine yapılan çalışmalarda [3], [6] istem tasarımının neden ayrı bir değişken olarak raporlanması gerektiğini somutlaştırır.

Buradan doğan tasarım önerisi açıktır: **ölçüt tek bir yerde tanımlanmalı**, hem insan etiketleme yönergesi hem de model istemi bu tek kaynaktan türetilmelidir. Mevcut kodda iki metin bağımsız durmakta ve bu, uyuşmazlığın tekrar oluşmasına açık bir kapı bırakır.

**Geçerlilik notu.** Yeniden değerlendirme sırasında sağlayıcının ücretsiz ortak havuzu kesintiye uğramış ve ilk turda dosyaların bir bölümü ücretli uç noktadan üretilmek zorunda kalınmıştır. Bu bölünme yöntem sınırıyla çakıştığı için karıştırıcı değişken oluşturmuş, dolayısıyla **60 dosyanın tamamı tek bir uç noktada (`google/gemma-4-26b-a4b-it`, Google) yeniden üretilmiştir**. Tablo 12'deki değerler bu tekleştirilmiş kümeden hesaplanmıştır ve her dosya kendisini üreten model ile sağlayıcıyı üst verisinde kaydeder.

Bu düzeltmenin gerekliliği ölçümle görülmüştür: karışık uç noktalı kümede Selenium + NanoLLM 0,890 doğrulukla önde görünürken, tekleştirilmiş kümede Agentic Search 0,890 ile öne geçmiştir. Özgüllükteki büyük değişim (0,000 → 0,846) ise her iki kümede de aynı kalmıştır; yani Bulgu 6 uç nokta seçiminden bağımsızdır, yöntemler arası ince sıralama ise değildir.

Orijinal 80 koşumun ücretsiz uç noktada yürütülmüş olması, v1 ile v2 arasında ikinci bir farklılık kaynağıdır. Kontrol grubunun (kural tabanlı yöntem, dil modeli kullanmaz) hiç değişmemesi bu kaynağın sonucu açıklayamayacağını gösterir, ancak tam kesinlik için orijinal koşumların da aynı uç noktada tekrarlanması gerekirdi.

**Ölçüm sınırlılıkları.**

- Ürün ve yöntem başına tek koşum yapılmıştır; varyans ve güven aralığı hesaplanmamıştır.
- Kategori başına iki ürün, yöntemleri aynı zeminde karşılaştırmak için yeterlidir ancak bir kategoriyi karakterize etmek için azdır.
- Etiketleme iki değerlendirici arasında bölünmüştür (134 ve 61 satır), ancak ikinci çalışma kitabı birincinin kapsadığı URL'leri dışladığından iki kümenin kesişimi sıfırdır. Hiçbir URL iki kez etiketlenmediği için değerlendiriciler arası anlaşma katsayısı (Cohen kappa) hesaplanamaz. Bu katsayının hesaplanabilmesi, aynı URL alt kümesinin her iki değerlendirici tarafından bağımsız etiketlenmesini gerektirir.
- Anahtar kelimeler deterministik modda üretilmiştir. Canlı modelle karşılaştırma yapılmış (Tablo 3a) ve deterministik üretecin ürün adındaki bilgiyi daha eksiksiz koruduğu ölçülmüştür; ancak canlı anahtar kelimelerle tam bir değerlendirme koşumu yapılmamıştır.
- Bölüm 6.1'deki yeniden değerlendirme tek bir sağlayıcı uç noktasında tekleştirilmiştir, ancak orijinal 80 koşum ücretsiz uç noktada yürütülmüştür. Kontrol grubunun hiç değişmemesi bu farkın sonucu açıklayamayacağını gösterse de, tam kesinlik orijinal koşumların da aynı uç noktada tekrarlanmasını gerektirirdi.
- Maliyetler 0,00 USD olarak raporlanmıştır; bu, kullanılan modelin ücretsiz katmanda olmasından ve arama maliyetinin sıfır kaydedilmesinden kaynaklanır ve gelecekteki koşumların ücretsiz olacağı anlamına gelmez.

---

# 7. CONCLUSION

Bu projede, yapılandırılmış ürün verisinden işlemsel niyetli arama sorguları üreten ve bu sorguların döndürdüğü web sonuçlarının e-ticaret uygunluğunu dört farklı yöntemle değerlendiren uçtan uca bir hat geliştirilmiştir. Dört yöntem, LangGraph tabanlı tek bir durum çizgesi üzerinde, aynı ürünler ve aynı anahtar kelimelerle çalıştırılmış; sonuçların uygunluğu yöntem tahminleri gizlenerek elle etiketlenmiş ve tüm yöntemler aynı insan etiketleri üzerinde ölçülmüştür.

Uygulama deneyiminin en öğretici yanı, ilk bakışta başarılı görünen bir sonucun daha yakından incelendiğinde ne kadar farklı okunabildiğidir. Ön değerlendirme aşamasında, henüz etiketlerin bir bölümü tamamlanmışken, yöntemlerin sıralaması bugünkünden farklı görünmekteydi; çünkü yöntemler o aşamada birbirinden farklı alt kümeler üzerinde ölçülüyordu. Etiket kapsamı %100'e ulaştığında hem sıralama değişmiş hem de asıl bulgunun doğruluk sıralamasında değil, sınıflandırma davranışında olduğu ortaya çıkmıştır: dil modeli tabanlı değerlendiricilerden biri hiçbir sonucu reddetmemiş, bir diğeri yüz sonuçtan yalnızca birini reddetmiştir. Bu, doğruluk metriğinin tek başına raporlanmasının yanıltıcı olabileceğini somut biçimde gösterir.

İkinci önemli deneyim, ölçüm altyapısının kendisinin de test edilmesi gerektiğidir. Proje sırasında bulunan iki hatanın ikisi de ölçüm hattındaydı ve her ikisi de sessiz veri kaybına yol açacak nitelikteydi: aynı sayfanın iki kez etiketlenmesi ve etiketsiz bir yöntemin rapordan tamamen düşmesi. Her iki durum için de gerileme testi yazılmıştır.

Üçüncü olarak, danışman geri bildiriminin ölçümle doğrulanabilmesi projenin yönünü belirlemiştir. "Tek kategori yeterli değil" eleştirisi, on kategoriye genişletme sonrasında sayısal olarak doğrulanmıştır: telefon kategorisi dört yöntem ortalamasında %100 doğruluk verirken diğer dokuz kategori %73,52'de kalmıştır.

Dördüncü ve belki en öğretici olanı, bir ölçüm sonucunu "sistemin başarısı" olarak kabul etmeden önce ölçüm tanımının kendisini denetlemenin değeridir. Dil modeli tabanlı değerlendiricilerin uygun olmayan sonuçları hiç reddedememesi, ilk bakışta model kapasitesi hakkında güçlü bir sonuç gibi görünmekteydi. Ölçüt tanımının iki ayrı yerde (etiketleme yönergesi ve sistem istemi) tutulduğu ve bu iki metnin birbirinden bağımsız evrildiği fark edildiğinde, aynı veri üzerinde yürütülen kontrollü bir yeniden değerlendirme sonucun büyük bölümünü açıklamıştır. Bu deneyimden çıkan mühendislik ilkesi, raporun 6.1 bölümünde tasarım önerisi olarak kaydedilmiştir: bir ölçüt tek bir yerde tanımlanmalı, onu kullanan bütün bileşenler o tek kaynaktan türetilmelidir.

## 7.1. Life-Long Learning

Proje boyunca ekibin kendi kendine öğrenmek durumunda kaldığı konular şunlardır:

**Durum çizgesi tabanlı orkestrasyon.** LangGraph, ders müfredatında yer almayan bir kütüphanedir. Düğüm, kenar, ortak durum ve koşullu geçiş kavramları resmî dokümantasyondan [11] ve kütüphanenin örneklerinden öğrenilmiştir. Kazanılan içgörü, orkestrasyonun yalnızca "adımları sırayla çalıştırmak" olmadığı; ortak durumun, aynı girdinin tüm yöntemlere değişmeden ulaşmasını garanti eden bir sözleşme işlevi gördüğüdür.

**Bilgi erişimi değerlendirme metodolojisi.** Uygunluk yargısı, test koleksiyonu, Cranfield paradigması ve değerlendirici değişkenliği kavramları literatürden öğrenilmiştir [2], [3]. Özellikle "etiket, sonucun özelliğidir; yöntemin özelliği değildir" ilkesi, tasarımın merkezine yerleşmiştir.

**Dengesiz veride metrik seçimi.** Doğruluğun dengesiz sınıf dağılımında neden yanıltıcı olduğu ve dengeli doğruluğun bu soruna nasıl yanıt verdiği literatürden öğrenilmiş [8] ve rapora doğrudan yansıtılmıştır.

**Tarayıcı otomasyonu ve kazıma dayanıklılığı.** Selenium ile arama sonucu toplamanın kırılganlığı, bot korumaları ve hız sınırlamaları uygulamalı olarak öğrenilmiştir. Oturum bazlı ilerleme kaydı ve devam edebilme yeteneği, bu deneyimin doğrudan sonucudur.

**Karakterizasyon testi disiplini.** Mevcut davranışı değiştirmeden önce onu teste alma yaklaşımı, projenin en değerli mühendislik pratiği olmuştur. Bu sayede on kategoriye genişletme sırasında önceki deneyin sonuçlarının bozulmadığı sürekli doğrulanabilmiştir.

Kullanılan kaynaklar: hakemli konferans ve dergi makaleleri (bkz. Kaynakça), kütüphanelerin resmî dokümantasyonları [11], [12] ve IETF standart belgesi [10].

## 7.2. Professional and Ethical Responsibilities of Engineers

Proje süresince aşağıdaki profesyonel ve etik sorumluluklar gözetilmiştir.

**Veri toplamada dürüstlük.** Bot korumaları aşılmamıştır. Cloudflare koruması nedeniyle erişilemeyen kaynak, korumayı aşmaya çalışmak yerine veri kaynağı listesinden çıkarılmıştır. Hız sınırlamalarına uyulmuş, istekler arası bekleme süresi artırılmıştır. robots.txt standardının [10] öngördüğü davranış normu benimsenmiştir. Araştırma amaçlı kazımanın etik çerçevesi literatürdeki tartışmalarla uyumlu biçimde ele alınmıştır [9].

**Sentetik ile gerçek verinin ayrılması.** Projede hem gerçek kazınmış veri hem de çevrimdışı çalışma için sentetik katalog vardır. Bu iki kaynak üst verideki `acquisition_mode` alanıyla açıkça ayrılmakta ve bu ayrımı koruyan otomatik testler vardır. Sentetik veri hiçbir koşulda gerçek veri gibi sunulmamıştır.

**Ölçüm dürüstlüğü.** Rapordaki tüm sayılar metrik dosyalarından otomatik olarak üretilir; elle yazılmaz. Bu, rapordaki değerlerin altındaki deneyden sapmasını yapısal olarak engeller. Ayrıca olumsuz bulgular gizlenmemiştir: yöntemlerden birinin hiçbir sonucu reddetmediği ve bir diğerinin önemsiz sınıflandırıcının altında kaldığı açıkça raporlanmıştır. Anahtar kelimelerin canlı dil modeliyle değil deterministik modda üretildiği de saklanmamıştır.

**Etiketleme yansızlığı.** Temel doğruluğu üreten kişiye yöntem tahminleri gösterilmemiştir. Bu, ölçülen doğrulukların herhangi bir yöntem lehine kaymasını önlemek için alınmış bilinçli bir önlemdir. Değerlendiricinin belirsiz bıraktığı satırlar, çalışma kitabı değiştirilmeden ayrı bir hakem dosyasında ve dayandıkları kural yazılarak çözülmüştür; böylece bir denetçi bu satırları dışlayıp metrikleri yeniden hesaplayabilir.

**Gizlilik ve güvenlik.** Kişisel veri toplanmamıştır. API anahtarları sürüm kontrolüne girmemekte, yalnızca anahtar içermeyen örnek dosya paylaşılır.

**Uygulanan standartlar.** ACM Etik ve Mesleki Davranış Kuralları'nın araştırma dürüstlüğü ve zarar vermeme ilkeleri ile IEEE Etik Kuralları'nın veriyi dürüst raporlama ilkesi gözetilmiştir. **[EKSİK VERİ: Bölümünüzün veya üniversitenizin resmî olarak atıf yapmanızı istediği belirli bir etik kod/yönerge varsa buraya ekleyiniz.]**

## 7.3. Contemporary Issues

Proje, güncel birkaç tartışmanın tam merkezinde yer alır.

**Yapay zekânın değerlendirici olarak kullanılması.** Dil modellerinin insan değerlendiricilerin yerini alıp alamayacağı, bilgi erişimi topluluğunda aktif bir tartışmadır [3]. Bu proje, tartışmaya küçük ve ücretsiz modeller açısından somut bir veri noktası ekler: ölçülen koşullarda küçük model, uygun olmayan sonuçların hiçbirini reddedememiştir. Bu, "yapay zekâ değerlendirebilir" iddiasının model ölçeğinden bağımsız genellenmemesi gerektiğini gösterir.

**Etmen tabanlı sistemlerin maliyet-fayda dengesi.** Etmen tabanlı yaklaşımlar güncel olarak büyük ilgi görür [7]. Bu projede etmen tabanlı yöntem en yüksek gecikmeyi getirmiş (ortalama 27,8395 saniye, kural tabanlı yöntemin yaklaşık beş katı) ancak ayırt etme kabiliyetinde anlamlı kazanım sağlamamıştır (özgüllük 0,0435). Bu, mimari karmaşıklığın otomatik olarak kalite getirmediğini gösterir.

**Veri erişiminin daralması.** Platformlar resmî veri kanallarını kısıtladıkça araştırmacılar kazımaya yönelmekte, bu da yeni etik ve hukuki sorunlar doğurur [9]. Bu proje, bir veri kaynağının bot koruması nedeniyle tamamen kullanılamaz hale gelmesini doğrudan yaşadı.

**Ücretsiz katman kotalarıyla araştırma yapmak.** Ticari model erişiminin maliyeti, öğrenci ve küçük ölçekli araştırmalar için gerçek bir kısıttır. Bu projede günlük kota sınırı, çok anahtarlı rotasyon ve deneyin oturumlara bölünmesiyle yönetilmiştir. Bu, kaynak kısıtının yalnızca bir zorluk değil, aynı zamanda mimari kararları biçimlendiren bir tasarım faktörü olduğunu gösterir.

**Kullanılan güncel araçlar.** Durum çizgesi tabanlı LLM orkestrasyonu (LangGraph), arama API'leri (Tavily), model yönlendirme platformları (OpenRouter), tarayıcı otomasyonu (Selenium WebDriver [12]) ve yapılandırılmış çıktı doğrulaması (Pydantic) projede fiilen kullanılmıştır.

## 7.4. Team Work

Proje iki kişilik bir ekiple yürütülmüştür: Ali Rubar Kal ve Atahan Bulut; ikisi de MEF Üniversitesi Bilgisayar Mühendisliği bölümü öğrencisidir. Sürüm kontrol geçmişine göre katkı dağılımı Ali Rubar Kal 26 işlem, Atahan Bulut 16 işlem biçimindedir.

**İş bölümü.** Ekip, işi teknik sorumluluk alanlarına göre bölmüştür. Veri toplama, kural tabanlı değerlendirme ve metrik/temel doğruluk altyapısı ağırlıklı olarak birinci üyede; yapılandırılmış anahtar kelime üretimi, dil modeli entegrasyonu, Tavily ve etmen tabanlı arama hatları ağırlıklı olarak ikinci üyede toplanmıştır. LangGraph orkestrasyonu, canlı değerlendirme koşumları ve kategori genişletmesi ortak yürütülmüştür. Etiketleme iki oturuma bölünmüş ve her oturumu bir ekip üyesi üstlenmiştir: birinci oturumdaki 134 satır bir üye, ikinci oturumdaki 61 satır diğer üye tarafından tamamlanmıştır. Bölünme iş yükünü paylaştırmış, ancak ikinci kitap birincinin URL'lerini dışladığı için iki değerlendiricinin ortak etiketlediği URL kalmamış ve anlaşma ölçümü mümkün olmamıştır.

**Organizasyon ve iletişim.** Koordinasyon, ortak bir Git deposu ve işlem mesajlarında tutulan gerekçe kayıtları üzerinden sağlanmıştır. İşlem mesajlarının yalnızca "ne değişti" değil "neden değişti" bilgisini de taşıması, ekip üyelerinin birbirinin kararlarını sonradan anlayabilmesini sağlamıştır.

**Değerlendirme.** Ekip kompozisyonunun güçlü yanı, iki üyenin farklı bileşenlerde derinleşerek paralel ilerleyebilmesiydi. Zayıf yanı, etiketleme iki kişi arasında bölünmüş olmasına rağmen örtüşen bir alt küme bırakılmadığı için etiket güvenilirliğinin ölçülememesi olmuştur. Geriye dönük bakıldığında, URL'lerin küçük bir alt kümesinin (örneğin %10'unun) her iki üye tarafından bağımsız etiketlenmesi, neredeyse aynı iş yüküyle bir anlaşma katsayısı üretebilir ve önemli bir metodolojik kazanım sağlayabilirdi.

**Dış paydaş.** Proje danışmanı, ara değerlendirmede tek kategorinin yetersizliğine ilişkin geri bildirim vermiş ve bu geri bildirim projenin ikinci aşamasının kapsamını doğrudan belirlemiştir. **[EKSİK VERİ: Şirket/kurum iş birliği yapıldıysa, birlikte çalışılan kişilerin pozisyonları ve alanları buraya eklenmelidir; proje kayıtlarında böyle bir iş birliği yoktur.]**

---

# APPENDIX A

**Sonuçların yeniden üretilmesi.** Aşağıdaki komutlar, rapordaki tüm sayıları sıfırdan yeniden üretir. Komutlar Windows PowerShell içindir.

```powershell
# 1. Temel doğruluğu iki çalışma kitabından ve hakem dosyasından üret
.\.venv\Scripts\python.exe src\evaluation\import_label_workbook.py `
  --workbook data\labels\label_review_session1.xlsx data\labels\label_review_session2.xlsx `
  --adjudication data\labels\multicategory_label_adjudications.csv `
  --output data\labels\multicategory_ground_truth.csv

# 2. Rapora girecek sonuç dosyalarını manifestte dondur
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py

# 3. Genel metrikleri hesapla
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py `
  --manifest data\evaluation\final_evaluation_manifest_multicategory.json `
  --output reports_multicategory\multicategory_evaluation_metrics.json

# 4. Kategori bazlı metrikleri hesapla
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py

# 5. Markdown raporu üret
.\.venv\Scripts\python.exe src\evaluation\multicategory_report.py

# 5b. Hata analizi: ayni sonuclari hizalanmis istemle yeniden yargila (Bolum 6.1)
.\.venv\Scripts\python.exe src\evaluation\rerun_with_aligned_prompt.py
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py `
  --results-directory results_multicategory_prompt_v2 `
  --output data\evaluation\final_evaluation_manifest_prompt_v2.json
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py `
  --manifest data\evaluation\final_evaluation_manifest_prompt_v2.json `
  --output reports_multicategory\prompt_v2_category_metrics.json `
  --markdown reports_multicategory\prompt_v2_category_metrics.md

# 6. Test paketini çalıştır (399 test)
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py"

# 7. Rapordaki sayilarin dosyalarla tutarliligini denetle
.\.venv\Scripts\python.exe src\evaluation\check_consistency.py
```

**Dondurulmuş telefon deneyinin yeniden üretilmesi.**

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py
.\.venv\Scripts\python.exe src\evaluation\final_report.py
```

**Ortam değişkenleri** (`.env` dosyasında tanımlanır; depoya girmez):

```
OPENROUTER_API_KEY=
OPENROUTER_API_KEY_2=      # isteğe bağlı; yalnızca AYRI bir hesabın anahtarı ek kota sağlar
NANO_LLM_MODEL=google/gemma-4-26b-a4b-it:free
AGENTIC_PLANNER_MODEL=google/gemma-4-26b-a4b-it:free
TAVILY_API_KEY=
```

---

# APPENDIX B

**B.1. Sonuç dosyası JSON şeması.** Her yöntem/ürün çifti için yazılan dosyanın zorunlu alanları:

| Alan | Tür | Açıklama |
|---|---|---|
| `product_id` | string | Ürün kimliği (örn. `ELK001`) |
| `keyword` | string | Dört yönteme de verilen ortak anahtar kelime |
| `method` | string | `tavily_llm`, `agentic_search`, `selenium_nano_llm`, `selenium_rule_based` |
| `execution_mode` | string | `live` veya `fake` |
| `provider` | string | Servis sağlayıcı adı |
| `model` | string | Kullanılan model kimliği |
| `prompt_version` | string | İstem sürümü |
| `runtime_seconds` | number | Çalışma süresi |
| `estimated_cost_usd` | number | Tahmini maliyet |
| `results` | array | Sonuç listesi (en fazla 5) |

Her sonuç öğesinin zorunlu alanları: `domain` (string), `url` (string, `http://` veya `https://` ile başlamalı), `title` (string), `snippet` (string), `predicted_relevant` (boolean), `relevance_score` (number, 0–1 aralığında).

**B.2. Temel doğruluk CSV şeması.**

| Sütun | Açıklama |
|---|---|
| `product_id` | Ürün kimliği |
| `keyword` | Anahtar kelime |
| `method` | **Boş bırakılır** — etiket, URL'yi döndüren tüm yöntemler için ortaktır |
| `domain` | Alan adı |
| `url` | Tam URL |
| `human_relevant` | `true` / `false` |
| `notes` | Değerlendirici notu, değerlendirici adı ve varsa hakem kararının gerekçesi |

**B.3. Hakem (adjudication) dosyası şeması.**

| Sütun | Açıklama |
|---|---|
| `product_id` | Ürün kimliği |
| `url` | Hakem kararı uygulanacak URL |
| `resolved_label` | Çözülen etiket (`true` / `false`) |
| `rule` | Kararın dayandığı kural veya emsal |
| `adjudicated_by` | Kararı veren |

**B.4. Bu deneyde çözülen beş belirsiz satır.**

| Ürün | Durum | Dayanılan kural / emsal | Sonuç |
|---|---|---|---|
| SBK003 | Ürün doğru (300 ml), stokta yok, fiyat görünmüyor | Yönerge: "Stokta olmamak sayfayı uygunsuz yapmaz"; sayfa tam olarak `variant_label` = 300 ml | true |
| SPM001 | Doğru ürün, 12'li paket olarak satılıyor | Birinci oturum emsali: Eti Burçak 114 g × 12 adet → false | false |
| SPM001 | Doğru ürün, 12'li paket olarak satılıyor | Aynı emsal | false |
| SPM003 | Doğru ürün, 50'li paket, stokta yok | Birinci oturum emsali: Lotus 250 g 6 adet → false | false |
| SPM003 | Doğru ürün, 250 g × 10 paket | Aynı emsal | false |

Beş kararın tamamı, değerlendiricinin birinci oturumda kendi verdiği kararlara ve yönerge sayfasındaki yazılı kurala dayandırılmıştır; bağımsız bir yargı kullanılmamıştır. Her karar temel doğruluk dosyasının `notes` alanına ham cevabı ve gerekçesiyle yazılmıştır.

**B.5. Kategori dağılımı.** Bkz. Tablo 3.

---

# ACKNOWLEDGEMENTS

Proje danışmanımıza, ara değerlendirmede tek bir ürün kategorisinin genellenebilirliği göstermek için yeterli olmadığına dair verdiği geri bildirim için teşekkür ederiz. Bu geri bildirim, projenin ikinci aşamasının kapsamını belirlemiş ve raporun en anlamlı bulgularından birinin (telefon kategorisinin setteki en kolay kategori olduğu) ortaya çıkmasını sağlamıştır. Danışmanımız Tuna Çakar'a teşekkür ederiz. **[EKSİK VERİ: teşekkür edilecek diğer kişi veya kurumlar varsa ekleyiniz.]**

---

# REFERENCES

[1] A. Broder, "A taxonomy of web search," *ACM SIGIR Forum*, vol. 36, no. 2, pp. 3–10, 2002.

[2] E. M. Voorhees, "Variations in relevance judgments and the measurement of retrieval effectiveness," *Information Processing & Management*, vol. 36, no. 5, pp. 697–716, 2000.

[3] G. Faggioli, L. Dietz, C. Clarke, G. Demartini, M. Hagen, C. Hauff, N. Kando, E. Kanoulas, M. Potthast, B. Stein, and H. Wachsmuth, "Perspectives on large language models for relevance judgment," arXiv preprint arXiv:2304.09161, 2023.

[4] J. Sachdev, S. D. Rosario, A. Phatak, H. Wen, S. Kirti, and C. Tripathy, "Automated query-product relevance labeling using large language models for e-commerce search," in *Proc. 8th Int. Conf. Natural Language Processing and Information Retrieval (NLPIR)*, 2024. doi: 10.1145/3711542.3711582. Also available as arXiv:2502.15990.

[5] K. Hosseini, T. Kober, J. Krapac, R. Vollgraf, W. Cheng, and A. Peleteiro Ramallo, "Retrieve, annotate, evaluate, repeat: Leveraging multimodal LLMs for large-scale product retrieval evaluation," in *Advances in Information Retrieval (ECIR 2025)*, Lecture Notes in Computer Science, Springer, 2025. doi: 10.1007/978-3-031-88708-6_10. Also available as arXiv:2409.11860.

[6] N. Mehrdad, H. Mohapatra, M. Bagdouri, P. Chandran, A. Magnani, X. Cai, A. Puthenputhussery, S. Yadav, T. Lee, C. Zhai, and C. Liao, "Large language models for relevance judgment in product search," presented at the LLM4Eval Workshop, ACM SIGIR, 2024. arXiv:2406.00247.

[7] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learning Representations (ICLR)*, 2023. arXiv:2210.03629.

[8] K. H. Brodersen, C. S. Ong, K. E. Stephan, and J. M. Buhmann, "The balanced accuracy and its posterior distribution," in *Proc. 20th Int. Conf. Pattern Recognition (ICPR)*, 2010, pp. 3121–3124. doi: 10.1109/ICPR.2010.764.

[9] M. A. Brown, A. Gruen, G. Maldoff, S. Messing, Z. Sanderson, and M. Zimmer, "Web scraping for research: Legal, ethical, institutional, and scientific considerations," *Big Data & Society*, 2025. doi: 10.1177/20539517251381686. Also available as arXiv:2410.23432.

[10] M. Koster, G. Illyes, H. Zeller, and L. Sassman, "Robots Exclusion Protocol," RFC 9309, Internet Engineering Task Force, Sep. 2022. doi: 10.17487/RFC9309.

[11] LangChain Inc., "LangGraph documentation." [Online]. Available: https://langchain-ai.github.io/langgraph/

[12] Selenium Project, "WebDriver documentation." [Online]. Available: https://www.selenium.dev/documentation/webdriver/
