# Multi-category evaluation, per method and category

Ground truth: `data/labels/multicategory_ground_truth.csv` · 20 products · 10 category groups · 4 methods

## Overall, per method

| method | labeled | accuracy | always-relevant | balanced acc. | precision | recall | specificity | F1 | said relevant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tavily_llm | 100 | 0.820 | 0.720 | 0.690 | 0.807 | 0.986 | 0.393 | 0.887 | 0.880 |
| agentic_search | 100 | 0.780 | 0.770 | 0.522 | 0.778 | 1.000 | 0.043 | 0.875 | 0.990 |
| selenium_nano_llm | 100 | 0.740 | 0.740 | 0.500 | 0.740 | 1.000 | 0.000 | 0.851 | 1.000 |
| selenium_rule_based | 99 | 0.707 | 0.758 | 0.509 | 0.761 | 0.893 | 0.125 | 0.822 | 0.889 |

## Accuracy per category group

| category group | labeled | tavily_llm | agentic_search | selenium_nano_llm | selenium_rule_based |
| --- | ---: | ---: | ---: | ---: | ---: |
| anne_bebek_oyuncak | 40 | 0.800 | 0.900 | 0.800 | 0.700 |
| elektronik_cep_telefonu | 40 | 1.000 | 1.000 | 1.000 | 1.000 |
| ev_yasam_ofis_kirtasiye | 40 | 0.700 | 0.900 | 0.800 | 0.800 |
| kitap_muzik_hobi | 40 | 1.000 | 1.000 | 1.000 | 0.800 |
| oto_bahce_yapi_market | 40 | 0.900 | 0.800 | 0.700 | 0.700 |
| petshop | 40 | 0.800 | 0.600 | 0.600 | 0.600 |
| saat_moda_taki_ayakkabi | 40 | 0.600 | 0.700 | 0.800 | 0.500 |
| saglik_bakim_kozmetik | 40 | 0.900 | 0.600 | 0.600 | 0.600 |
| spor_outdoor | 39 | 0.800 | 0.600 | 0.400 | 0.667 |
| supermarket | 40 | 0.700 | 0.700 | 0.700 | 0.700 |

## Share of labeled URLs that are relevant, per category

| category group | labeled | relevant share |
| --- | ---: | ---: |
| anne_bebek_oyuncak | 40 | 0.825 |
| elektronik_cep_telefonu | 40 | 0.950 |
| ev_yasam_ofis_kirtasiye | 40 | 0.775 |
| kitap_muzik_hobi | 40 | 0.950 |
| oto_bahce_yapi_market | 40 | 0.750 |
| petshop | 40 | 0.650 |
| saat_moda_taki_ayakkabi | 40 | 0.700 |
| saglik_bakim_kozmetik | 40 | 0.675 |
| spor_outdoor | 39 | 0.564 |
| supermarket | 40 | 0.625 |
