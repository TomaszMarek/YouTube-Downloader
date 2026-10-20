<div align="center">

# YouTube Downloader

Wydajny, desktopowy menedżer multimediów YouTube dla systemu Windows.  
Wielowątkowa kolejka zadań, selektywny bufor playlist, konwersja do MP3 oraz obsługa formatów panoramicznych.

</div>

---

## Spis treści

- [Prezentacja interfejsu](#prezentacja-interfejsu)
- [Funkcjonalności](#funkcjonalności)
- [Architektura i wyzwania inżynieryjne](#architektura-i-wyzwania-inżynieryjne)
- [Struktura projektu](#struktura-projektu)
- [Wdrożenie i uruchomienie](#wdrożenie-i-uruchomienie)
- [Stos technologiczny](#stos-technologiczny)
- [Plan rozwoju (Roadmap)](#plan-rozwoju-roadmap)
---

## Prezentacja interfejsu

### 1. Główny widok kolejki pobierania
Menedżer zadań z aktywną telemetrią (postęp, prędkość, rozmiar danych) oraz możliwością anulowania i usuwania wpisów.
<p align="center">
  <img src="assets/preview-queue.png" alt="Kolejka pobierania" width="100%">
</p>

### 2. Selektywny wybór utworów z playlisty
Lokalny cache metadanych w pamięci RAM pozwalający na zaznaczanie wybranych pozycji przed pobraniem.
<p align="center">
  <img src="assets/preview-selection.png" alt="Wybór utworów z playlisty" width="100%">
</p>

### 3. Rejestr historii pobrań
Baza lokalna z historią ukończonych pobrań, etykietami formatów oraz szybkim dostępem do plików na dysku.
<p align="center">
  <img src="assets/preview-history.png" alt="Rejestr historii pobrań" width="100%">
</p>

---

## Funkcjonalności

<table>
<tr>
<td width="33%" valign="top">

### Pobieranie i konwersja

- **Profile rozdzielczości**: od 480p, przez 720p, 1080p i 1440p, aż do 4K (2160p), scalane asynchronicznie przez FFmpeg.
- **Ekstrakcja MP3**: konwersja strumienia audio do 192 kbps wraz z okładką albumu w tagach ID3.
- **Wielowątkowość**: dedykowana kolejka pobierania (`ThreadPoolExecutor`) chroniąca interfejs użytkownika przed zamrożeniem.
- **Detekcja duplikatów**: weryfikacja fizycznej obecności pliku na dysku zapobiega nadpisywaniu i ponownemu pobieraniu tych samych danych.
- **Sprzątanie przerwanych zadań**: bezpieczne usuwanie pozostałości plików tymczasowych (`.part`, `.ytdl`) po anulowaniu lub błędzie.
- **Filmy niepubliczne**: pełna obsługa bezpośrednich linków do filmów ze statusem *Unlisted*.

</td>
<td width="33%" valign="top">

### Zaawansowane playlisty

- **Interaktywny selektor**: opcja pobrania całej playlisty lub wskazania konkretnych pozycji przed rozpoczęciem transferu.
- **Buforowanie w pamięci (RAM cache)**: jednokrotnie pobrana playlista otwiera się natychmiast, bez powtórnych zapytań sieciowych.
- **Pełna responsywność wiersza**: kliknięcie w dowolne miejsce kafelka przełącza stan zaznaczenia elementu.
- **Podsumowania z fleksją**: zliczanie fizycznie pobranych plików z zachowaniem polskiej odmiany (`1 utwór`, `3 utwory`, `12 utworów`).

</td>
<td width="33%" valign="top">

### Automatyzacja i UX

- **Inteligentny schowek**: najechanie kursorem na pole adresu weryfikuje schowek systemowy i automatycznie wkleja poprawny URL bez `Ctrl+V`.
- **Sanityzacja adresów**: automatyczne odcinanie parametrów śledzących z zachowaniem identyfikatorów wideo i playlist.
- **Filtrowanie na żywo**: dynamiczne wyszukiwanie w historii pobranych plików w czasie rzeczywistym.
- **Retencja ustawień**: automatyczny zapis ścieżki docelowej oraz preferencji formatu w pliku konfiguracyjnym (`settings.json`).
- **Telemetria**: precyzyjny odczyt prędkości transferu, pobranych megabajtów, ETA oraz etapu scalania strumieni.

</td>
</tr>
</table>

---

## Architektura i wyzwania inżynieryjne

<details>
<summary><strong>1. Zarządzanie stanem i licznik sesji playlisty (QueueManager)</strong></summary>

<br>

Domyślne metadane platformy operują na bezwzględnych pozycjach utworów w obrębie całej playlisty (`playlist_index`). Wybranie np. 4 pozycji ze środka listy (utwory 10–13) w standardowych implementacjach prowadzi do mylącego zapisu postępu w interfejsie (`[10/4]`, `[11/4]`).

W warstwie `QueueManager` zaimplementowano lokalny licznik sekwencji sesyjnej:

- oddziela fizyczny indeks utworu w serwisie od stanu bieżącej kolejki,
- prezentuje czytelną dla użytkownika numerację `[1/4]... [4/4]`,
- wyklucza zadania anulowane z bazy historii, eliminując błędy odwołań do niekompletnych plików.

</details>

<details>
<summary><strong>2. Normalizacja rozdzielczości formatów panoramicznych (2.40:1)</strong></summary>

<br>

Materiały panoramiczne i kinowe (np. zwiastuny filmowe, teledyski) charakteryzują się mniejszą wysokością klatki niż standard 16:9 (np. 1920x800 px zamiast nominalnego 1920x1080 px).

Weryfikacja jakości oparta wyłącznie na wysokości skutkowałaby fałszywym ostrzeżeniem o pobraniu gorszego standardu. Moduł `normalize_resolution_label` bada geometrię klatki oraz jej szerokość, poprawnie klasyfikując wideo do odpowiednich progów rozdzielczości (480p, 720p, 1080p, 1440p, 4K).

</details>

<details>
<summary><strong>3. Dwufazowa alokacja ścieżek dla zbiorów złożonych</strong></summary>

<br>

Pobieranie wyselekcjonowanych pozycji bezpośrednio przez silnik gubi kontekst nadrzędnej playlisty, co w szablonach zapisu powoduje tworzenie podkatalogów o nazwie `NA/`.

Rozwiązano to poprzez dwufazowe przetwarzanie:

- wstępne pobranie metadanych spisu w trybie płaskim (`extract_flat`),
- oczyszczenie nazwy albumu ze znaków niedozwolonych w systemie Windows (`\ / : * ? " < > |`),
- fizyczne utworzenie katalogu docelowego i skierowanie do niego pobieranych plików.

</details>

<details>
<summary><strong>4. Izolacja wątków i maszyna stanów UI</strong></summary>

<br>

Pętla główna interfejsu (`MainThread`) nie wykonuje żadnych blokujących operacji wejścia/wyjścia ani zapytań sieciowych. Wszystkie operacje realizowane są w tle i raportowane przez kolejkę komunikatów `EventBus`.

Przejście do widoków modalnych (np. selekcja utworów) blokuje kontrolki nadrzędne, uniemożliwiając równoległe wywołanie kolidujących operacji, a anulowane wątki pobierania poprawnie zwalniają uchwyty i czyszczą karty zadań.

</details>

---

## Struktura projektu

```text
youtube-downloader/
│
├── assets/                 # Zrzuty ekranu dokumentujące interfejs użytkownika
│   ├── preview-queue.png
│   ├── preview-selection.png
│   └── preview-history.png
│
├── core/
│   ├── downloader.py       # Silnik pobierania, integracja yt-dlp i FFmpeg
│   ├── events.py           # Magistrala zdarzeń (EventBus) łącząca wątki robocze z GUI
│   ├── models.py           # Modele danych (dataclass, enum)
│   └── queue_manager.py    # Orkiestracja wątków, licznik sesji, weryfikacja plików
│
├── gui/
│   ├── components/         # Modułowe paski interfejsu (TopBar, PathBar, NavBar)
│   ├── views/              # Widoki ekranowe (HistoryView, SelectionView)
│   ├── app.py              # Główne okno programu i zarządca stanów UI
│   └── task_card.py        # Karta pojedynczego zadania pobierania z telemetrią
│
├── utils/
│   ├── config.py           # Odczyt i zapis konfiguracji użytkownika (JSON)
│   ├── formatters.py       # Normalizacja rozdzielczości, formatowanie jednostek
│   ├── history.py          # Lokalna baza danych pobranych pozycji
│   └── paths.py            # Rozwiązywanie ścieżek systemowych i lokalizacji FFmpeg
│
├── .gitignore              # Reguły wykluczeń dla środowiska, binariów i cache
├── main.py                 # Główny punkt wejścia do aplikacji
└── requirements.txt        # Jawny spis zależności produkcyjnych
```

---

## Wdrożenie i uruchomienie

<table>
<tr>
<td width="50%" valign="top">

### Wersja samodzielna (`.exe`)

Dedykowana dla użytkowników końcowych, bez wymagań systemowych.

1. Przejdź do sekcji [**Releases**](../../releases) po prawej stronie repozytorium.
2. Pobierz najnowszy plik **`YouTubeDownloader.exe`**.
3. Uruchom program dwuklikiem.

> **Uwaga:** binaria FFmpeg oraz środowisko wykonawcze zostały skonsolidowane wewnątrz pliku wykonywalnego. Program nie wymaga instalacji Pythona.

</td>
<td width="50%" valign="top">

### Uruchomienie ze źródeł (Python)

Dedykowane do celów rozwojowych i audytu kodu.

**Wymagania wstępne:**

- `Python >= 3.10`
- `ffmpeg.exe` oraz `ffprobe.exe` w katalogu projektu lub w zmiennej środowiskowej `PATH`

</td>
</tr>
</table>

### Procedura startowa ze źródeł

```bash
# 1. Klonowanie repozytorium
git clone https://github.com/TomaszMarek/youtube-downloader.git
cd youtube-downloader

# 2. Utworzenie i aktywacja środowiska wirtualnego
python -m venv .venv
.venv\Scripts\activate

# 3. Instalacja wymaganych pakietów
pip install -r requirements.txt

# 4. Inicjalizacja procesu aplikacji
python main.py
```

---

## Stos technologiczny

| Kategoria | Komponent | Zastosowanie |
| :--- | :--- | :--- |
| Język bazowy | Python 3.10+ | Logika biznesowa, orkiestracja zadań |
| Interfejs GUI | CustomTkinter | Responsywny interfejs graficzny w trybie ciemnym |
| Silnik ekstrakcji | yt-dlp | Parsowanie strumieni DASH i metadanych serwisu |
| Przetwarzanie multimediów | FFmpeg | Multipleksowanie strumieni A/V, konwersja do MP3, tagowanie ID3 |
| Kompilacja binarna | PyInstaller | Budowanie autonomicznego pliku wykonywalnego `.exe` |

---

## Plan rozwoju (Roadmap)

- **Lokalizacja metadanych (język polski)**: Wymuszenie nagłówków `Accept-Language: pl-PL` oraz flagi `extractor_args` w `yt-dlp`, eliminujące automatyczne tłumaczenie polskich tytułów filmów na język angielski.
- **Inteligentne pomijanie YouTube Shorts**: Wdrożenie reguł filtrujących (`aspect_ratio`, detekcja URL `/shorts/` oraz czasu trwania $\le$ 60s) w oknie wyboru utworów z playlisty i w silniku pobierania.
- **Uwierzytelnianie ciasteczkami sesyjnymi**: Obsługa parametru `cookiesfrombrowser` w konfiguracji, umożliwiająca pobieranie filmów prywatnych z uprawnieniami konta oraz materiałów z ograniczeniem wiekowym.

---
