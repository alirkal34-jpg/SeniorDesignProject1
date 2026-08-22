> **TRANSLATION IN PROGRESS.** This English version currently covers the
> title page through section 2.1. Everything after that point still lives
> only in `SDP_rapor_TR.md`, which remains the complete and authoritative
> version. Do not submit this file until the translation is finished.

# PRODUCT-DRIVEN KEYWORD GENERATION AND A FOUR-METHOD COMPARISON OF E-COMMERCE RELEVANCE IN SEARCH RESULTS

**COMP491 — Senior Design Project I**

**Students:** Atahan Bulut, Ali Rubar Kal
**Advisor:** Tuna Çakar
**Date:** **[MISSING DATA: submission date (dd/mm/yyyy)]**

MEF UNIVERSITY
FACULTY OF ENGINEERING
DEPARTMENT OF COMPUTER ENGINEERING

---

## ABSTRACT

**PRODUCT-DRIVEN KEYWORD GENERATION AND A FOUR-METHOD COMPARISON OF E-COMMERCE RELEVANCE IN SEARCH RESULTS**

Atahan Bulut, Ali Rubar Kal
MEF University, Faculty of Engineering, Department of Computer Engineering
Advisor: Tuna Çakar
AUGUST, 2026

This project generates search queries carrying transactional intent from structured product data, and evaluates the e-commerce relevance of the web search results those queries return using four different methods. The methods compared are: Selenium-based collection with rule-based domain scoring, Selenium-based collection with small-scale language model (NanoLLM) evaluation, the Tavily search API with NanoLLM evaluation, and agentic search built around a plan–search–evaluate loop. All four methods are orchestrated on a single directed acyclic graph in LangGraph, which guarantees that the same keyword reaches all four methods unchanged for every product.

The system was built on 489 real products from 10 category groups collected from Akakçe. The evaluation was carried out on a 20-product subset formed by selecting two products of two different brands from each category: 20 products × 4 methods = 80 live runs, 399 search results and 46 distinct domains. Result relevance was labeled by hand through a workbook in which the methods' predictions were hidden; human labels were obtained for 193 unique URLs, and those labels covered all 399 results (100% coverage).

The measured overall accuracy is 76.19%. In the first measurement the substantive finding was not in the accuracy ranking but in the classification behaviour: Selenium + NanoLLM called 100 of 100 results "relevant", giving a specificity of 0.000 and a balanced accuracy of 0.500; Agentic Search called 99 of them "relevant". The error analysis that followed established the cause of this behaviour: there is a definitional mismatch between the prompt given to the evaluator model and the human labeling rule — the prompt counts category pages as relevant while the rule does not. When the prompt was aligned with the rule and the same results were re-judged, with no search repeated and no label changed, the specificity of Selenium + NanoLLM rose from 0.000 to 0.846 and overall accuracy rose from 76.19% to 82.46%. The rule-based method, which uses no language model, served as the control group and did not change at all. In the per-category breakdown, the phone category proved the easiest category with 100% accuracy averaged over the four methods, while the remaining nine groups averaged 73.52%.

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
   3.2. Solution Method: A LangGraph-Based Four-Method Comparison Pipeline
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
   6.1. Error analysis: the source of the low specificity
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

- Table 1. The evolution of the method families used in relevance assessment, by period, and the method corresponding to each in this project
- Table 2. The project's realised work breakdown and schedule
- Table 3. Category taxonomy and collected product counts
- Table 3a. Distinguishing attributes dropped by the live model
- Table 4. Type distribution of the trusted e-commerce domain table
- Table 5. Software tools and versions used in the project
- Table 6. Risk analysis: realised and anticipated risks
- Table 7. Source code and test code size
- Table 8. Overall performance comparison of the four methods
- Table 9. Per-method confusion matrix
- Table 10. Accuracy by category group
- Table 11. Comparison of the frozen phone experiment with the multi-category experiment
- Table 12. The effect of prompt alignment on the four methods

## LIST OF FIGURES

- Figure 1. Node structure of the end-to-end LangGraph
- Figure 2. The four-method comparison subgraph
- Figure 3. The agentic search subgraph
- Figure 4. Use case diagram
- Figure 5. Data flow and component diagram
- Figure 6. Labeling and measurement sequence diagram

## LIST OF ABBREVIATIONS

| Abbreviation | Description |
|---|---|
| API | Application Programming Interface |
| CSV | Comma-Separated Values |
| DAG | Directed Acyclic Graph |
| FN | False Negative |
| FP | False Positive |
| IR | Information Retrieval |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| NanoLLM | The small-scale, free-tier language model evaluator used in this project |
| SEO | Search Engine Optimization |
| TN | True Negative |
| TP | True Positive |
| UML | Unified Modeling Language |
| WBS | Work Breakdown Structure |

---

# 1. INTRODUCTION

When a user runs an e-commerce search, how many of the returned pages are actually useful for buying? That ratio is a direct measure of two things: the ranking quality of the search engine, and the seller's investment in search engine optimization. This project addresses two connected problems. The first is the automatic generation of search queries carrying transactional intent from structured product data (brand, model, variant label, category). The second is the automatic assessment of the e-commerce relevance of the web results those queries return, and the objective comparison of different assessment approaches on the same data.

The four methods represent different cost and capability points. This choice is deliberate. The methods are:

1. Results collected through browser automation are scored against a fixed table of trusted domains.
2. The same results are evaluated with a small language model.
3. Results from a commercial search API are evaluated with the same language model.
4. An agentic method puts planning, searching and evaluation into a loop.

All four methods run on a single LangGraph. That graph guarantees that the same product and the same keyword reach all of them.

In the first phase of the project only the smartphone category was used. Following advisor feedback, the dataset was expanded to ten category groups so that the pipeline's ability to generalise across different search intents and different product structures could be demonstrated, and the comparison was repeated on this expanded set. This report presents the design, implementation and measured results of the expanded experiment.

## 1.1. Motivation

The importance of working on this project rests on three points.

First, studies of search quality cannot scale as long as relevance assessment cannot be automated. In the information retrieval literature, relevance judgments are classically produced by human assessors, and this is the most expensive component of the Cranfield paradigm [2]. In recent years, whether large language models can take over these judgments partly or entirely has been an active debate [3], [6]. This project offers a concrete measurement by testing that debate in a Turkish e-commerce context and with small, free-tier models.

Second, the difference between a method "giving high accuracy" and a method "actually discriminating" is frequently overlooked in practice. The measurements in this project show that on a dataset where the large majority of returned results are already relevant, even a classifier that rejects nothing can achieve high accuracy. For this reason accuracy is not reported alone in this report but together with specificity and balanced accuracy [8].

Third, the parties who would benefit directly from the results are identifiable. Sellers managing a product catalogue can see which keyword pattern brings which kind of page, and how much manual review burden each automatic evaluator could remove. Price comparison platforms could build a similar measurement pipeline to audit their catalogue matching quality. Academically, comparing four methods on the same products, the same keywords and the same human labels shows the effect of method choice in isolation.

## 1.2. Broad Impact

The problem of relevance assessment has been approached with different families of methods in different periods of the information retrieval field. Table 1 summarises that evolution and the counterpart of each method family in this project.

**Table 1.** The evolution of the method families used in relevance assessment and the method corresponding to each in this project.

| Year | Method family | Evaluation data | Counterpart in this project |
|---|---|---|---|
| 2000 | Human relevance judgments (Cranfield / TREC) [2] | TREC ad hoc collections | Ground truth produced by hand for 193 unique URLs |
| 2002 | Query intent classification [1] | AltaVista query logs and a user survey | Transactional keyword generation and the transactional-purpose criterion |
| 2023 | Agentic reasoning and acting loop [7] | HotpotQA, FEVER, ALFWorld, WebShop | The Agentic Search method (plan → search → evaluate → aggregate) |
| 2023–2025 | Relevance judgment with language models [3], [4], [5], [6] | Product search and web search collections | The Selenium + NanoLLM and Tavily + NanoLLM methods |

### 1.2.1. Global Impact of the solution

The global impact of the solution follows from the method being relatively independent of language and market. The system's input is a structured product record and its output is a result list written to a shared JSON schema; the search provider, the evaluator model and the trusted domain table are each configuration items. Because of this separation, the same pipeline can be reused for the e-commerce ecosystem of a different country by changing only the domain table and the category taxonomy. Furthermore, because the project measures the limits of small, free-tier models in relevance assessment, it produces a finding that transfers directly to researchers and small businesses without a budget for large commercial models.

### 1.2.2. Economic Impact of the solution

The economic impact has two sides. On the cost side, the estimated provider cost recorded for all 80 live runs in this project is 0.00 USD, because the OpenRouter model used operates on a free tier and the Tavily search cost was recorded as zero for this experiment. This shows that the measurement pipeline can be built within free-tier quotas; it does not mean that future runs will be free.

On the benefit side, how much automatic assessment could reduce the manual labeling burden was measured. Labeling the 399 results by hand was completed in two sessions. According to the measurements, only one of the methods (Tavily + NanoLLM) was able to reject 39.29% of the irrelevant results; the remaining three methods filter out practically nothing and therefore do not meaningfully reduce the manual review burden. Compared with studies reporting near-human accuracy in large-scale product search assessment [5], this finding indicates that model scale and prompt design are decisive.

For the project's direct monetary cost items: **[MISSING DATA: please enter your assumptions for hardware (personal computers), software licences and the hourly rate for human resources; these values are not in the project records.]**

### 1.2.3. Environmental Impact of the solution

Environmental impact should be assessed through computational intensity. The measured average runtimes differ by more than a factor of five between methods: the rule-based method takes an average of 5.5505 seconds per run, while the agentic method takes 27.8395 seconds. This matters because it shows that the method giving the highest accuracy does not also carry the highest computational cost: Tavily + NanoLLM, which gives the highest accuracy, completes in an average of 12.0785 seconds, roughly half the time of the agentic method. In terms of energy consumption, not choosing an unnecessarily heavier method is a direct saving.

Two precautions were also taken on the data collection side. A delay was placed between requests, so no unnecessary load was put on the target sites. Products collected in a previous session were not fetched again but carried over. The collection metadata records this: `carried_over_from_previous_run: 489`, `collected_this_run: 0`.

No server-side energy consumption or carbon equivalent measurement was made: **[MISSING DATA: please enter a measured energy consumption / carbon value if one exists; it is not in the project records.]**

### 1.2.4. Societal Impacts of the solution

The societal impact concerns whether the consumer can actually reach the product from a search result. In this project the relevance criterion requires the page both to be the product named in the query (including the stated variant) and to carry transactional purpose. The measurements show that 53 of the 193 labeled URLs (27.5%) do not meet this criterion; that is, in roughly a quarter of the returned results the user cannot reach a purchasable page for the product they were looking for. This ratio was also measured to vary considerably by category: the share of relevant results is 95.00% in the phone and book/music/hobby categories, but falls to 56.41% in the sports/outdoor category.

The societal risk of automatic evaluators is also made concrete in this project. An evaluator that filters nothing out does not protect the user from irrelevant pages, however well it looks on the accuracy metric. For this reason the report argues that automatic evaluators should be reported not by accuracy alone but together with their ability to reject.

### 1.2.5. Legal Issues related to the project

The legal dimension of the project lies mainly in the data collection stage. The data was collected from publicly accessible product listing pages on Akakçe. The following principles were applied during collection:

- **Bot protection was not bypassed.** The Cimri site was not reachable because of Cloudflare-based protection, and no attempt was made to bypass that protection; the site was disabled entirely as a data source. The rate limiting encountered on Akakçe was managed by increasing the delay between requests and by splitting the collection work across several sessions. Seven collection sessions were recorded in total.
- **Robots Exclusion Protocol.** robots.txt was standardised by the IETF as RFC 9309 [10]. Compliance with these directives by automated clients is accepted as an established norm independently of any legal obligation [9].
- **No personal data was collected.** The only fields collected are product identifier, product name, brand, category, source link and product attributes; no personal data was collected.
- **Credentials were kept out of the repository.** API keys are held in a `.env` file and excluded from version control via `.gitignore`; the repository contains only `.env.example`, which holds no keys.
- **Synthetic and real data were kept apart.** The synthetic catalogue and the scraped data are distinguished by the `acquisition_mode` field in the metadata (`synthetic` / `scraped`), and automated tests preserve that distinction. Synthetic data is never presented as real data under any circumstances.

In terms of intellectual property, the collected data is factual product information rather than original expression, and it was used solely for academic assessment. The legal, ethical and institutional dimensions of web scraping for research purposes are discussed in detail in the literature [9].

---

# 2. PROJECT DEFINITION AND PLANNING

## 2.1. Project Definition
