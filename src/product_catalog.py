"""Deterministic offline catalog for the ten advisor-specified categories.

This module is the API-free source used to build and test the multi-category
pipeline. It is deliberately kept separate from ``product_scraper``: the
scraper reaches real e-commerce sites, this module does not touch the network
at all, so unit tests and demonstrations stay reproducible.

Data produced here is **synthetic**. It is realistic in shape - Turkish brands,
plausible model names, real category structure - but it is generated, not
measured. Any dataset written from this module records
``acquisition_mode: synthetic`` in its metadata, and must never be presented as
scraped market data. Replace it by running ``product_scraper.py`` with the
Selenium provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus


REFERENCE_SEARCH_URL = "https://www.cimri.com/arama?q={query}"


@dataclass(frozen=True)
class CatalogProduct:
    """One generated product before it is written to the dataset."""

    product_name: str
    brand: str
    category: str
    category_group: str
    attributes: dict[str, Any] = field(default_factory=dict)
    # Scraped products carry the real listing URL. Generated products have
    # none, and fall back to a search URL that still reaches the product.
    source_url: str = ""

    def reference_url(self) -> str:
        """Return the product's own URL, or a traceable HTTPS lookup URL."""

        if self.source_url:
            return self.source_url

        return REFERENCE_SEARCH_URL.format(
            query=quote_plus(self.product_name)
        )


@dataclass(frozen=True)
class CategorySpec:
    """How one category group generates its products."""

    category: str
    product_lines: dict[str, tuple[str, ...]]
    variants: tuple[str, ...]

    def combinations(self) -> list[tuple[str, str, str]]:
        """Return (brand, model, variant) triples in a stable order."""

        triples: list[tuple[str, str, str]] = []

        for variant in self.variants:
            for brand, models in self.product_lines.items():
                for model in models:
                    triples.append((brand, model, variant))

        return triples


# The variant label is the shopping-relevant spec that also becomes part of the
# generated search keyword. Category-specific numeric attributes are parsed back
# out of it, so the label and the attributes can never disagree.
CATEGORY_SPECS: dict[str, CategorySpec] = {
    "elektronik_cep_telefonu": CategorySpec(
        category="Cep Telefonu",
        product_lines={
            "Apple": ("iPhone 16", "iPhone 16 Pro", "iPhone 15"),
            "Samsung": ("Galaxy S25", "Galaxy S24 FE", "Galaxy A56"),
            "Xiaomi": ("Redmi Note 14", "Redmi Note 14 Pro", "Poco X7"),
            "Oppo": ("Reno 12", "A80", "Find X8"),
            "Realme": ("13 Pro", "C67", "Note 60"),
        },
        variants=("128 GB", "256 GB", "512 GB", "1024 GB"),
    ),
    "ev_yasam_ofis_kirtasiye": CategorySpec(
        category="Ev ve Ofis",
        product_lines={
            "Karaca": ("Retro Çaydanlık", "Emaye Tencere Seti", "Kahve Fincanı"),
            "English Home": ("Pamuklu Nevresim", "Banyo Havlusu", "Masa Örtüsü"),
            "Faber Castell": ("Kurşun Kalem Seti", "Keçeli Kalem Seti", "Defter Seti"),
            "Tefal": ("Granit Tava", "Ütü Masası", "Düdüklü Tencere"),
            "Bambum": ("Bambu Saklama Kabı", "Servis Tahtası", "Baharatlık Seti"),
        },
        variants=("Tekli", "2 Parça", "4 Parça", "6 Parça"),
    ),
    "anne_bebek_oyuncak": CategorySpec(
        category="Anne, Bebek ve Oyuncak",
        product_lines={
            "Prima": ("Aktif Bebek Bezi", "Premium Care Bezi", "Pants Külot Bez"),
            "Chicco": ("Biberon Seti", "Oyun Halısı", "Mama Sandalyesi"),
            "Lego": ("City İtfaiye Seti", "Classic Yapım Kutusu", "Duplo Tren Seti"),
            "Pampers": ("Sleep & Play Bezi", "Islak Mendil", "Yeni Bebek Bezi"),
            "Fisher Price": ("Müzikli Oyuncak", "Aktivite Küpü", "Zıpzıp At"),
        },
        variants=("Küçük Boy", "Orta Boy", "Büyük Boy", "Ekonomik Paket"),
    ),
    "saat_moda_taki_ayakkabi": CategorySpec(
        category="Saat, Moda ve Aksesuar",
        product_lines={
            "Casio": ("G-Shock Kol Saati", "Vintage Kol Saati", "Edifice Kol Saati"),
            "Nike": ("Air Max Spor Ayakkabı", "Revolution Koşu Ayakkabısı", "Court Sneaker"),
            "Adidas": ("Samba Sneaker", "Duramo Ayakkabı", "Gazelle Sneaker"),
            "LC Waikiki": ("Slim Fit Gömlek", "Basic Tişört", "Kot Pantolon"),
            "Atasay": ("Altın Kolye", "Gümüş Bileklik", "Pırlanta Yüzük"),
        },
        variants=("38 Numara", "40 Numara", "42 Numara", "44 Numara"),
    ),
    "kitap_muzik_hobi": CategorySpec(
        category="Kitap, Müzik ve Hobi",
        product_lines={
            "Yapı Kredi Yayınları": (
                "Tutunamayanlar",
                "Saatleri Ayarlama Enstitüsü",
                "Kürk Mantolu Madonna",
            ),
            "İş Bankası Kültür Yayınları": ("Suç ve Ceza", "Sefiller", "Dönüşüm"),
            "Can Yayınları": ("Körlük", "Fahrenheit 451", "Simyacı"),
            "Fender": ("Akustik Gitar", "Gitar Teli Seti", "Elektro Gitar"),
            "Ravensburger": ("1000 Parça Puzzle", "500 Parça Puzzle", "Ahşap Puzzle"),
        },
        variants=("Ciltli", "Karton Kapak", "Özel Baskı", "Cep Boy"),
    ),
    "spor_outdoor": CategorySpec(
        category="Spor ve Outdoor",
        product_lines={
            "Decathlon": ("Kamp Çadırı", "Uyku Tulumu", "Trekking Bot"),
            "Under Armour": ("Antrenman Tişörtü", "Spor Çanta", "Termal Alt Giyim"),
            "Salomon": ("Outdoor Ayakkabı", "Su Geçirmez Mont", "Trekking Bastonu"),
            "Wilson": ("Basketbol Topu", "Tenis Raketi", "Futbol Topu"),
            "Reebok": ("Yoga Matı", "Dambıl Seti", "Direnç Bandı"),
        },
        variants=("Tek Kişilik", "İki Kişilik", "Standart", "Profesyonel"),
    ),
    "saglik_bakim_kozmetik": CategorySpec(
        category="Sağlık, Bakım ve Kozmetik",
        product_lines={
            "Nivea": ("Nemlendirici Krem", "Duş Jeli", "Deodorant"),
            "L'Oreal": ("Elseve Şampuan", "Saç Kremi", "Saç Boyası"),
            "Garnier": ("Micellar Su", "Yüz Temizleme Jeli", "Güneş Kremi"),
            "Bioderma": ("Sensibio Solüsyon", "Atoderm Krem", "Photoderm Sprey"),
            "Elidor": ("Onarıcı Şampuan", "Saç Bakım Maskesi", "Saç Serumu"),
        },
        variants=("200 ml", "300 ml", "400 ml", "500 ml"),
    ),
    "oto_bahce_yapi_market": CategorySpec(
        category="Oto, Bahçe ve Yapı Market",
        product_lines={
            "Bosch": ("Akülü Vidalama", "Darbeli Matkap", "Çim Biçme Makinesi"),
            "Makita": ("Avuç Taşlama", "Şarjlı Testere", "Kırıcı Delici"),
            "Castrol": ("Motor Yağı", "Fren Hidroliği", "Antifriz"),
            "Karcher": ("Basınçlı Yıkama Makinesi", "Islak Kuru Süpürge", "Cam Temizleyici"),
            "Gardena": ("Bahçe Hortumu", "Sulama Seti", "Budama Makası"),
        },
        variants=("12V", "18V", "24V", "Standart"),
    ),
    "petshop": CategorySpec(
        category="Petshop",
        product_lines={
            "Royal Canin": ("Yavru Kedi Maması", "Yetişkin Köpek Maması", "Indoor Kedi Maması"),
            "Pro Plan": ("Somonlu Kedi Maması", "Kuzulu Köpek Maması", "Sterilised Kedi Maması"),
            "Whiskas": ("Tavuklu Kedi Maması", "Yaş Kedi Maması", "Ton Balıklı Kedi Maması"),
            "Pedigree": ("Biftekli Köpek Maması", "Ödül Köpek Maması", "Kuzulu Köpek Konservesi"),
            "Catsan": ("Hijyenik Kedi Kumu", "Doğal Kedi Kumu", "Topaklanan Kedi Kumu"),
        },
        variants=("1.5 kg", "3 kg", "10 kg", "15 kg"),
    ),
    "supermarket": CategorySpec(
        category="Süpermarket",
        product_lines={
            "Ülker": ("Çikolatalı Gofret", "Bisküvi Paketi", "Kakaolu Kek"),
            "Eti": ("Kraker Paketi", "Çikolatalı Kek", "Burçak Bisküvi"),
            "Torku": ("Toz Şeker", "Ayçiçek Yağı", "Makarna"),
            "Pınar": ("Süt", "Beyaz Peynir", "Kaşar Peyniri"),
            "Fairy": ("Bulaşık Deterjanı", "Sıvı Sabun", "Çamaşır Deterjanı"),
        },
        variants=("500 g", "1000 g", "1500 g", "2000 g"),
    ),
}


def _numeric_prefix(variant_label: str) -> float | None:
    """Read the leading number out of a variant label such as '256 GB'."""

    token = variant_label.split(" ", 1)[0].replace(",", ".")

    try:
        return float(token)
    except ValueError:
        return None


def build_attributes(
    category_group: str,
    brand: str,
    model: str,
    variant_label: str,
    sequence_number: int,
) -> dict[str, Any]:
    """Build the category-specific attributes for one generated product.

    The keys returned here must cover every attribute the taxonomy marks as
    required for the category, including the universal ``variant_label``.
    """

    attributes: dict[str, Any] = {"variant_label": variant_label}
    measurement = _numeric_prefix(variant_label)

    if category_group == "elektronik_cep_telefonu":
        attributes["storage_gb"] = int(measurement or 128)
        attributes["ram_gb"] = (4, 6, 8, 12)[sequence_number % 4]
    elif category_group == "ev_yasam_ofis_kirtasiye":
        attributes["room_or_use"] = (
            "Mutfak",
            "Yatak Odası",
            "Banyo",
            "Ofis",
        )[sequence_number % 4]
    elif category_group == "anne_bebek_oyuncak":
        attributes["age_range"] = (
            "0-6 ay",
            "6-12 ay",
            "1-3 yaş",
            "3-6 yaş",
        )[sequence_number % 4]
    elif category_group == "saat_moda_taki_ayakkabi":
        attributes["size_label"] = variant_label
        attributes["color"] = (
            "Siyah",
            "Beyaz",
            "Lacivert",
            "Bordo",
        )[sequence_number % 4]
    elif category_group == "kitap_muzik_hobi":
        attributes["creator"] = brand
    elif category_group == "spor_outdoor":
        attributes["discipline"] = (
            "Kamp",
            "Koşu",
            "Fitness",
            "Outdoor",
        )[sequence_number % 4]
    elif category_group == "saglik_bakim_kozmetik":
        attributes["volume_ml"] = int(measurement or 200)
    elif category_group == "oto_bahce_yapi_market":
        attributes["power_or_volume"] = variant_label
    elif category_group == "petshop":
        attributes["animal_type"] = (
            "Kedi" if "Kedi" in model else "Köpek"
        )
        attributes["weight_kg"] = measurement or 1.5
    elif category_group == "supermarket":
        attributes["net_weight_g"] = int(measurement or 500)

    return attributes


def generate_category_products(
    category_group: str,
    limit: int,
) -> list[CatalogProduct]:
    """Generate a deterministic, duplicate-free product list for one category."""

    specification = CATEGORY_SPECS.get(category_group)

    if specification is None:
        raise KeyError(
            f"No offline catalog is defined for category: {category_group}"
        )

    combinations = specification.combinations()

    if len(combinations) < limit:
        raise ValueError(
            f"{category_group}: the catalog can build "
            f"{len(combinations)} products but {limit} were requested."
        )

    products: list[CatalogProduct] = []

    for sequence_number, (brand, model, variant) in enumerate(
        combinations[:limit],
        start=1,
    ):
        products.append(
            CatalogProduct(
                product_name=f"{brand} {model} {variant}",
                brand=brand,
                category=specification.category,
                category_group=category_group,
                attributes=build_attributes(
                    category_group=category_group,
                    brand=brand,
                    model=model,
                    variant_label=variant,
                    sequence_number=sequence_number,
                ),
            )
        )

    return products
