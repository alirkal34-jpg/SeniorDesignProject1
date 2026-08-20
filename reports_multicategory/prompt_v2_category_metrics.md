# Multi-category evaluation, per method and category

Ground truth: `data/labels/multicategory_ground_truth.csv` · 20 products · 10 category groups · 4 methods

## Overall, per method

| method | labeled | accuracy | always-relevant | balanced acc. | precision | recall | specificity | F1 | said relevant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic_search | 100 | 0.890 | 0.770 | 0.852 | 0.934 | 0.922 | 0.783 | 0.928 | 0.760 |
| selenium_nano_llm | 100 | 0.850 | 0.740 | 0.849 | 0.940 | 0.851 | 0.846 | 0.894 | 0.670 |
| tavily_llm | 100 | 0.850 | 0.720 | 0.820 | 0.901 | 0.889 | 0.750 | 0.895 | 0.710 |
| selenium_rule_based | 99 | 0.707 | 0.758 | 0.509 | 0.761 | 0.893 | 0.125 | 0.822 | 0.889 |

## Accuracy per category group

| category group | labeled | agentic_search | selenium_nano_llm | tavily_llm | selenium_rule_based |
| --- | ---: | ---: | ---: | ---: | ---: |
| anne_bebek_oyuncak | 40 | 0.700 | 0.800 | 0.800 | 0.700 |
| elektronik_cep_telefonu | 40 | 1.000 | 0.400 | 1.000 | 1.000 |
| ev_yasam_ofis_kirtasiye | 40 | 1.000 | 1.000 | 0.900 | 0.800 |
| kitap_muzik_hobi | 40 | 1.000 | 1.000 | 0.900 | 0.800 |
| oto_bahce_yapi_market | 40 | 0.800 | 0.800 | 0.800 | 0.700 |
| petshop | 40 | 0.800 | 0.800 | 0.900 | 0.600 |
| saat_moda_taki_ayakkabi | 40 | 0.800 | 0.900 | 0.800 | 0.500 |
| saglik_bakim_kozmetik | 40 | 1.000 | 1.000 | 0.800 | 0.600 |
| spor_outdoor | 39 | 0.800 | 0.800 | 0.800 | 0.667 |
| supermarket | 40 | 1.000 | 1.000 | 0.800 | 0.700 |

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
