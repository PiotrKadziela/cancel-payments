# Cancel Payments

Skrypt do automatycznego anulowania płatności w systemie Papaya dla zamówień anulowanych w Magento.

## Funkcjonalności

- Pobieranie listy anulowanych zamówień z bazy danych Magento
- Sprawdzanie płatności powiązanych z zamówieniami w bazie Papaya
- Anulowanie płatności przez API Papaya
- **Logowanie postępu do pliku CSV** - umożliwia bezpieczne przerywanie i wznawianie skryptu
- Szczegółowe logowanie do pliku `.log`

## Logowanie postępu (CSV)

Skrypt automatycznie zapisuje postęp przetwarzania do pliku CSV, co pozwala na:

- **Bezpieczne przerywanie skryptu** (Ctrl+C) bez utraty postępu
- **Automatyczne wznawianie** od miejsca gdzie skrypt został przerwany
- **Unikanie ponownego przetwarzania** tych samych zamówień

### Struktura pliku CSV

Plik `progress_log.csv` zawiera następujące kolumny:

| Kolumna | Opis |
|---------|------|
| `order_increment_id` | Identyfikator zamówienia z Magento |
| `timestamp` | Data i czas ostatniej aktualizacji (ISO 8601) |
| `status` | Aktualny status przetwarzania |
| `payment_id` | Identyfikator płatności w Papaya (jeśli dotyczy) |
| `error_message` | Szczegóły błędu (jeśli wystąpił) |

### Statusy przetwarzania

- `fetched_from_magento` - Zamówienie pobrane z bazy Magento, oczekuje na sprawdzenie w Papaya
- `no_action_needed` - Zamówienie nie wymaga anulowania płatności (brak płatności lub już anulowane)
- `payment_canceled_success` - Płatność została pomyślnie anulowana przez API
- `payment_canceled_error` - Błąd podczas anulowania płatności przez API

### Przykładowy plik CSV

```csv
order_increment_id,timestamp,status,payment_id,error_message
100001234,2026-02-10T10:30:45.123456,payment_canceled_success,98765,
100001235,2026-02-10T10:31:12.456789,no_action_needed,,
100001236,2026-02-10T10:31:45.789012,fetched_from_magento,,
100001237,2026-02-10T10:32:10.234567,payment_canceled_error,98766,"API returned 500: Internal Server Error"
```

## Wymagania

- Python 3.7+
- Dostęp do bazy danych Magento (MySQL)
- Dostęp do bazy danych Papaya (MySQL)
- Dostęp do API Papaya

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/PiotrKadziela/cancel-payments.git
cd cancel-payments
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

3. Skopiuj przykładowy plik konfiguracji i uzupełnij dane:
```bash
cp .env.example .env
nano .env
```

## Konfiguracja

Edytuj plik `.env` i uzupełnij następujące parametry:

### Baza danych Magento
```env
MAGENTO_DB_HOST=localhost
MAGENTO_DB_PORT=3306
MAGENTO_DB_USER=magento_user
MAGENTO_DB_PASSWORD=magento_password
MAGENTO_DB_NAME=magento_db
```

### Baza danych Papaya
```env
PAPAYA_DB_HOST=localhost
PAPAYA_DB_PORT=3306
PAPAYA_DB_USER=papaya_user
PAPAYA_DB_PASSWORD=papaya_password
PAPAYA_DB_NAME=papaya_db
```

### API Papaya
```env
PAPAYA_API_URL=https://api.papaya.example.com/cancel
PAPAYA_API_KEY=your_api_key_here
```

### Logi i postęp
```env
PROGRESS_LOG_FILE=progress_log.csv
LOG_FILE=cancel_payments.log
LOG_LEVEL=INFO
```

## Użytkowanie

### Pierwsze uruchomienie

```bash
python cancel_payments.py
```

Skrypt:
1. Pobierze anulowane zamówienia z Magento
2. Zapisze je natychmiast do pliku CSV ze statusem `fetched_from_magento`
3. Sprawdzi każde zamówienie w bazie Papaya
4. Anuluje płatności przez API i zaktualizuje statusy w CSV

### Wznawianie przerwanego skryptu

Jeśli skrypt został przerwany (np. Ctrl+C, błąd połączenia):

```bash
python cancel_payments.py
```

Skrypt automatycznie:
- Wczyta plik CSV z poprzedniego uruchomienia
- Pominie zamówienia już przetworzone
- Kontynuuje od miejsca gdzie zakończył

**Nie musisz niczego robić ręcznie** - wystarczy ponownie uruchomić skrypt.

### Rozpoczęcie od nowa

Jeśli chcesz przetworzyć wszystkie zamówienia ponownie, usuń plik CSV:

```bash
rm progress_log.csv
python cancel_payments.py
```

## Przepływ przetwarzania

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Pobranie zamówień z Magento                              │
│    → Zapisanie do CSV ze statusem 'fetched_from_magento'   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Filtrowanie zamówień                                     │
│    → Pomiń zamówienia już przetworzone                      │
│    → Przetwarzaj tylko nowe i 'fetched_from_magento'        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Sprawdzenie w bazie Papaya                               │
│    ├─ Brak płatności                                        │
│    │  → Aktualizacja CSV: 'no_action_needed'               │
│    └─ Znaleziono płatności                                  │
│       → Przejście do kroku 4                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Anulowanie płatności przez API                           │
│    ├─ Sukces                                                │
│    │  → Aktualizacja CSV: 'payment_canceled_success'       │
│    └─ Błąd                                                  │
│       → Aktualizacja CSV: 'payment_canceled_error'          │
└─────────────────────────────────────────────────────────────┘
```

## Logi

### Plik logów
Wszystkie operacje są logowane do pliku `cancel_payments.log` (lub według konfiguracji w `.env`).

### Plik CSV
Plik `progress_log.csv` zawiera szczegółowy stan przetwarzania każdego zamówienia.

## Obsługa błędów

- **Błąd połączenia z bazą danych** - Skrypt zakończy się z błędem. Popraw konfigurację i uruchom ponownie.
- **Błąd API Papaya** - Szczegóły błędu zostaną zapisane w CSV w kolumnie `error_message`. Zamówienie otrzyma status `payment_canceled_error`.
- **Przerwanie przez użytkownika (Ctrl+C)** - Postęp zostanie zapisany, uruchom skrypt ponownie aby kontynuować.
- **Uszkodzony plik CSV** - Skrypt zaloguje ostrzeżenie i utworzy nowy plik.

## Bezpieczeństwo

⚠️ **Ważne:** 
- **Nie commituj** pliku `.env` do repozytorium (jest w `.gitignore`)
- **Nie commituj** plików CSV z logami postępu (są w `.gitignore`)
- Plik `.env` zawiera wrażliwe dane dostępowe
- Regularnie zmieniaj hasła i klucze API

## Rozwój

### Struktura projektu

```
cancel-payments/
├── cancel_payments.py   # Główny skrypt
├── requirements.txt     # Zależności Python
├── .env.example        # Przykładowa konfiguracja
├── .gitignore          # Pliki ignorowane przez git
└── README.md           # Dokumentacja
```

### Testowanie

Przed uruchomieniem na produkcji:
1. Przetestuj połączenia z bazami danych
2. Sprawdź klucz API Papaya
3. Uruchom skrypt na małym zbiorze danych testowych
4. Zweryfikuj poprawność zapisów w CSV

## Licencja

MIT

## Autor

Piotr Kądziela

## Wsparcie

W przypadku problemów:
1. Sprawdź plik `cancel_payments.log`
2. Sprawdź plik `progress_log.csv`
3. Zweryfikuj konfigurację w `.env`
4. Otwórz issue na GitHubie