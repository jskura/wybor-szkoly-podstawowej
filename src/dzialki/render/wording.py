"""Every Polish string the surface renders, in one file.

One file, because a string that appears twice drifts, and because the
terminology lint and the reviewer both want one place to read. Nothing here is
formatted: numbers arrive from ``format.py`` and are substituted by the builder.

The interface is Polish (D15). Code identifiers stay English.
"""

from __future__ import annotations

# --- headings -------------------------------------------------------------

PLOT_CHECK = "Sprawdzenie działki"
FLOW_BLOCK = "Podobne oferty (przepływ, {window})"
STOCK_BLOCK = "Podobne oferty (stan, wszystkie aktywne)"
GUS_BLOCK = "Ceny transakcyjne · powiat {powiat} · {quarter}"
COMPARABLE_SET = "Podobne oferty — {count}"
COMPARABLE_SET_HEADING = "Podobne oferty"
VERDICT = "WERDYKT"
PROVENANCE = "Źródło i metoda"
UNCERTAINTY_PANEL = "Ocena pewności"

# --- basis labels ---------------------------------------------------------

BASIS_LABELS: dict[str, str] = {
    "flow": "przepływ",
    "stock": "stan",
    "gus_powiat": "poziom powiatu, dane kwartalne",
    "derived": "wyliczone z mediany podobnych ofert, nie zaobserwowana cena",
}

FLOW_WINDOW = "ostatnie {window}"
STOCK_FLOW_GAP = "stan wyżej niż przepływ"
FLOW_STOCK_GAP = "przepływ wyżej niż stan"

# --- values ---------------------------------------------------------------

MEDIAN_VALUE = "mediana {price}"
MEAN_VALUE = "średnia {price}"
SAMPLE_SIZE = "n = {n}"

# --- the spread, and D69 --------------------------------------------------

SPREAD_IQR = "zakres międzykwartylowy {range}"
SPREAD_MIN_MAX = "zakres {range}"
SPREAD_UNAVAILABLE = "zakres niedostępny — GUS publikuje tylko średnią"

# --- provenance -----------------------------------------------------------

PROVENANCE_SOURCE = "Źródło: {sources}"
PROVENANCE_AS_OF = "Stan na: {date}"
PROVENANCE_METHOD = "Metoda: {method_version}"
PROVENANCE_N = "Liczba obserwacji: n = {n}"

# --- staleness ------------------------------------------------------------

STALENESS = "dane sprzed {days} · ostatnie pobranie {date}"

# --- price labels (D68) ---------------------------------------------------

PRICE_TYPE_LABELS: dict[str, str] = {
    "offering": "cena ofertowa",
    "sales": "cena transakcyjna",
}

PRICE_KIND_LABELS: dict[str, str] = {
    "asking": "oferta",
    "auction_start": "cena wywoławcza",
    "tender": "cena przetargowa",
    "transaction": "transakcja",
}

# --- absence (U7) ---------------------------------------------------------

ABSENCE_TEXTS: dict[str, str] = {
    "not_yet_crawled": "Brak danych — tej gminy jeszcze nie zebraliśmy",
    "no_listings": "Brak danych — w tej gminie nie ma ofert",
    "out_of_scope": "Brak danych — ta gmina jest poza zasięgiem narzędzia",
    "too_few_comparables": "Brak danych — za mało podobnych ofert",
}

ABSENCE_ACTIONS: dict[str, str] = {
    "not_yet_crawled": "jeszcze nie zebraliśmy — sprawdź później",
    "no_listings": "brak ofert w tej gminie",
    "out_of_scope": "poza zasięgiem narzędzia",
    "too_few_comparables": "za mało podobnych ofert, żeby porównać",
}

# --- unknown attributes (U6) ----------------------------------------------

UNKNOWN_TEXTS: dict[str, str] = {
    "buildability": "brak danych planistycznych — sprawdź w gminie",
    "road_access": "brak danych o dojeździe — sprawdź w gminie",
    "utilities": "brak danych o mediach — sprawdź w gminie",
    "soil_class": "brak danych o klasie gruntu — sprawdź w gminie",
}

# The standing product limit, distinct from the per-plot unknown above.
NO_PLAN_CHECK = "Nie sprawdzamy planu — nie wiemy, czy można budować"
FROM_THE_ADVERT = "z ogłoszenia"

# --- uncertainty (U10, U11) -----------------------------------------------

NOTE_THIN_NARROW = "Mało podobnych ofert — wynik orientacyjny"
NOTE_THIN_WIDE = "Zakres szeroki — mało podobnych ofert"
NOTE_WIDE = "Zakres szeroki — ceny w tej gminie bardzo się różnią"
NOTE_NO_SPREAD = "Nie znamy rozrzutu — GUS publikuje tylko średnią"

UNCERTAINTY_VOCABULARY: tuple[str, ...] = (
    NOTE_THIN_NARROW,
    NOTE_THIN_WIDE,
    NOTE_WIDE,
    NOTE_NO_SPREAD,
)

OUT_OF_DEPTH = "za mało danych, żeby ocenić — to jest orientacja, nie wycena"

# --- the verdict (U5) -----------------------------------------------------

VERDICT_ABOVE = "Powyżej górnej granicy zakresu przepływu ({range})"
VERDICT_BELOW = "Poniżej dolnej granicy zakresu przepływu ({range})"
VERDICT_WITHIN = "W zakresie przepływu ({range})"

VERDICT_FORMS: tuple[str, ...] = (VERDICT_ABOVE, VERDICT_BELOW, VERDICT_WITHIN)

VERDICT_BASIS = "Podstawa: {offers}, ta sama gmina, {band}, {window}"
UNCERTAINTY_BASIS = "Podstawa: {offers}, {window}"

# --- sensitivity notes (U13) ----------------------------------------------

SENSITIVITY_TEXTS: dict[str, str] = {
    "buildability": "gdyby ta działka miała plan miejscowy, porównania byłyby inne",
    "road_access": (
        "gdyby dojazd był drogą gminną, a nie służebnością, porównania byłyby inne"
    ),
    "utilities": "gdyby media były na działce, a nie w granicy, porównania byłyby inne",
}

GMINA_OFFICE = "Urząd Gminy {gmina}"
BINDING_DOCUMENT = "wypis i wyrys"

# --- the honest disclosure (`21` §7.2) ------------------------------------

HONEST_DISCLOSURE = (
    "Ten tool porównuje ceny ofertowe. Nie jest wyceną rzeczoznawcy i nie "
    "sprawdza, czy na działce można budować. Przy małej liczbie porównań wynik "
    "jest orientacyjny."
)

# --- the comparable list --------------------------------------------------

COMPARABLE = "{price} · {area} · gmina {gmina} · {date}"
EXCLUDE_CONTROL = "nie pasuje"

# --- the plot-check header ------------------------------------------------

HEADER = "{area} · gmina {gmina} · {price}"

# --- loading and failure, per component -----------------------------------

LOADING_TEXTS: dict[str, str] = {
    "plot_check_header": "wczytywanie danych o działce…",
    "verdict_block": "wczytywanie werdyktu…",
    "comparable_set": "wczytywanie podobnych ofert…",
    "flow_aggregate_block": "wczytywanie podobnych ofert…",
    "stock_aggregate_block": "wczytywanie wszystkich aktywnych ofert…",
    "gus_sales_block": "wczytywanie cen transakcyjnych…",
    "uncertainty_panel": "wczytywanie oceny pewności…",
    "provenance_panel": "wczytywanie źródeł…",
}

ERROR_TEXTS: dict[str, str] = {
    "plot_check_header": (
        "Nie udało się odczytać ogłoszenia — wpisz powierzchnię i gminę ręcznie"
    ),
    "verdict_block": (
        "Nie udało się policzyć werdyktu — podobne oferty powyżej są aktualne"
    ),
    "comparable_set": (
        "Nie udało się pobrać podobnych ofert — cena z ogłoszenia powyżej jest aktualna"
    ),
    "flow_aggregate_block": (
        "Nie udało się policzyć przepływu — stan poniżej jest aktualny"
    ),
    "stock_aggregate_block": (
        "Nie udało się policzyć stanu — przepływ powyżej jest aktualny"
    ),
    "gus_sales_block": (
        "Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne"
    ),
    "uncertainty_panel": ("Nie udało się ocenić pewności — liczby powyżej są aktualne"),
    "provenance_panel": (
        "Nie udało się odczytać źródeł — liczby powyżej pochodzą z bazy"
    ),
}
