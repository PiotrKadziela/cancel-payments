# cancel-payments

Automatyczny skrypt Python do anulowania płatności w systemie Papaya dla zamówień anulowanych w Magento.

## Opis działania

Skrypt wykonuje następujące operacje:

1. **Pobiera anulowane zamówienia z Magento** - Wyszukuje zamówienia anulowane w określonym przedziale czasowym, które mają więcej niż jedną płatność z niepustym identyfikatorem transakcji.

2. **Znajduje nieanulowane płatności w Papaya** - Sprawdza, które płatności powiązane z anulowanymi zamówieniami nie zostały jeszcze anulowane w systemie Papaya.

3. **Anuluje płatności przez API Papaya** - Wysyła żądania anulowania płatności do API Papaya i loguje wyniki operacji.

4. **Śledzi postęp w pliku CSV** - Zapisuje stan przetwarzania każdego zamówienia, umożliwiając wznowienie po przerwaniu.

## Nowe funkcje

### Śledzenie statusu w CSV

Skrypt automatycznie tworzy plik CSV (np. `payment_cancellation_status_20240101_to_20241231.csv`) zawierający:
- Status każdego zamówienia
- Informacje o próbach anulowania
- Szczegóły błędów
- Znaczniki czasu

### Wznowienie po przerwaniu

Jeśli skrypt zostanie przerwany, można go uruchomić ponownie - automatycznie wznowi przetwarzanie od miejsca zatrzymania, pomijając już przetworzone zamówienia.

## Wymagania systemowe

- Python 3.7 lub nowszy
- Dostęp do bazy danych Magento (odczyt)
- Dostęp do bazy danych Papaya (odczyt)
- Dostęp do API Papaya (zapis - anulowanie płatności)

## Instalacja

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/PiotrKadziela/cancel-payments.git
cd cancel-payments
```

### 2. Utworzenie środowiska wirtualnego (opcjonalnie, ale zalecane)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows
```

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

## Konfiguracja

### 1. Utworzenie pliku konfiguracyjnego

Skopiuj plik `.env.example` do `.env`:

```bash
cp .env.example .env
```

### 2. Edycja pliku `.env`

Uzupełnij plik `.env` rzeczywistymi danymi dostępowymi:

```env
# Baza danych Magento
MAGENTO_DB_HOST=magento-db.example.com
MAGENTO_DB_PORT=3306
MAGENTO_DB_NAME=magento_production
MAGENTO_DB_USER=magento_readonly_user
MAGENTO_DB_PASSWORD=secure_password_here

# Baza danych Papaya
PAPAYA_DB_HOST=papaya-db.example.com
PAPAYA_DB_PORT=3306
PAPAYA_DB_NAME=papaya_production
PAPAYA_DB_USER=papaya_readonly_user
PAPAYA_DB_PASSWORD=secure_password_here

# API Papaya
PAPAYA_API_URL=https://api.papaya.example.com
PAPAYA_API_LOGIN=api_user
PAPAYA_API_PASSWORD=api_password_here

# Parametry skryptu
DATE_FROM=2024-01-01
DATE_TO=2024-12-31
```

### Parametry konfiguracyjne

#### Baza danych Magento

- **MAGENTO_DB_HOST** - Adres serwera bazy danych Magento
- **MAGENTO_DB_PORT** - Port bazy danych (domyślnie 3306)
- **MAGENTO_DB_NAME** - Nazwa bazy danych Magento
- **MAGENTO_DB_USER** - Użytkownik z dostępem do odczytu
- **MAGENTO_DB_PASSWORD** - Hasło użytkownika

#### Baza danych Papaya

- **PAPAYA_DB_HOST** - Adres serwera bazy danych Papaya
- **PAPAYA_DB_PORT** - Port bazy danych (domyślnie 3306)
- **PAPAYA_DB_NAME** - Nazwa bazy danych Papaya
- **PAPAYA_DB_USER** - Użytkownik z dostępem do odczytu
- **PAPAYA_DB_PASSWORD** - Hasło użytkownika

#### API Papaya

- **PAPAYA_API_URL** - Bazowy URL API Papaya (bez końcowego /)
- **PAPAYA_API_LOGIN** - Login do Basic Authentication
- **PAPAYA_API_PASSWORD** - Hasło do Basic Authentication

#### Parametry skryptu

- **DATE_FROM** - Data początkowa przedziału czasowego (format: YYYY-MM-DD)
- **DATE_TO** - Data końcowa przedziału czasowego (format: YYYY-MM-DD)

## Uruchomienie

### Podstawowe uruchomienie

```bash
python cancel_payments.py
```

### Uruchomienie z logowaniem do pliku

Skrypt automatycznie zapisuje logi do pliku `cancel_payments.log` oraz wyświetla je w konsoli.

### Śledzenie postępu w CSV

Po pierwszym uruchomieniu skrypt utworzy plik CSV (np. `payment_cancellation_status_20240101_to_20241231.csv`) zawierający szczegółowe informacje o statusie przetwarzania każdego zamówienia.

#### Struktura pliku CSV:

```csv
order_id,payment_id,requires_cancellation,cancellation_attempted,cancellation_status,error_message,timestamp
100000001,12345,True,True,SUCCESS,,2024-12-15 10:30:45
100000002,,False,False,NOT_REQUIRED,,2024-12-15 10:30:46
100000003,12346,True,True,FAILED,API returned status 500,2024-12-15 10:30:50
100000004,12347,True,False,PENDING,,2024-12-15 10:30:30
```

#### Statusy anulowania:

- **PENDING** - Zamówienie oczekuje na przetworzenie
- **NOT_REQUIRED** - Zamówienie nie wymaga anulowania płatności (brak płatności w Papaya)
- **SUCCESS** - Płatność została pomyślnie anulowana
- **FAILED** - Anulowanie płatności nie powiodło się (szczegóły w kolumnie error_message)

### Wznowienie po przerwaniu

Jeśli skrypt zostanie przerwany (np. przez Ctrl+C lub błąd), można go uruchomić ponownie:

```bash
python cancel_payments.py
```

Skrypt automatycznie:
1. Wykryje istniejący plik CSV
2. Wczyta aktualny stan przetwarzania
3. Wznowi przetwarzanie tylko dla zamówień oczekujących (status PENDING i nie próbowano anulować)
4. Pominie zamówienia już przetworzone

### Przykładowe wyjście - pierwsze uruchomienie

```
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - Starting Payment Cancellation Script
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - Configuration loaded successfully for date range: 2024-01-01 to 2024-12-31
2024-12-15 10:30:00 - INFO - CSV filename: payment_cancellation_status_20240101_to_20241231.csv
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - NEW RUN MODE: No CSV file found, starting fresh
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - Step 1: Fetching canceled orders from Magento...
2024-12-15 10:30:01 - INFO - Connected to database: magento_production
2024-12-15 10:30:02 - INFO - Found 15 canceled orders in Magento
2024-12-15 10:30:02 - INFO - Saved 15 orders to CSV with initial status
2024-12-15 10:30:02 - INFO - Closed connection to database: magento_production
2024-12-15 10:30:02 - INFO - Step 2: Fetching non-canceled payments from Papaya for 15 orders...
2024-12-15 10:30:02 - INFO - Connected to database: papaya_production
2024-12-15 10:30:03 - INFO - Found 12 non-canceled payments in Papaya
2024-12-15 10:30:03 - INFO - Updated CSV with payment information for 15 orders
2024-12-15 10:30:03 - INFO - Closed connection to database: papaya_production
2024-12-15 10:30:03 - INFO - Step 3: Canceling 12 payments via Papaya API...
2024-12-15 10:30:04 - INFO - Successfully canceled payment 12345
2024-12-15 10:30:05 - INFO - Successfully canceled payment 12346
...
2024-12-15 10:30:15 - INFO - Cancellation complete: 12 succeeded, 0 failed
2024-12-15 10:30:15 - INFO - ================================================================================
2024-12-15 10:30:15 - INFO - Payment Cancellation Summary:
2024-12-15 10:30:15 - INFO -   Total orders in CSV: 15
2024-12-15 10:30:15 - INFO -   Orders requiring cancellation: 12
2024-12-15 10:30:15 - INFO -   Orders not requiring cancellation: 3
2024-12-15 10:30:15 - INFO -   Payments successfully canceled: 12
2024-12-15 10:30:15 - INFO -   Payments failed to cancel: 0
2024-12-15 10:30:15 - INFO -   CSV file location: /path/to/payment_cancellation_status_20240101_to_20241231.csv
2024-12-15 10:30:15 - INFO - ================================================================================
2024-12-15 10:30:15 - INFO - Script completed successfully
```

### Przykładowe wyjście - wznowienie po przerwaniu

```
2024-12-15 11:00:00 - INFO - ================================================================================
2024-12-15 11:00:00 - INFO - Starting Payment Cancellation Script
2024-12-15 11:00:00 - INFO - ================================================================================
2024-12-15 11:00:00 - INFO - Configuration loaded successfully for date range: 2024-01-01 to 2024-12-31
2024-12-15 11:00:00 - INFO - CSV filename: payment_cancellation_status_20240101_to_20241231.csv
2024-12-15 11:00:00 - INFO - ================================================================================
2024-12-15 11:00:00 - INFO - RESUME MODE: CSV file found, resuming from previous run
2024-12-15 11:00:00 - INFO - ================================================================================
2024-12-15 11:00:00 - INFO - Loaded 15 orders from CSV: payment_cancellation_status_20240101_to_20241231.csv
2024-12-15 11:00:00 - INFO - Found 3 pending orders to process from CSV
2024-12-15 11:00:00 - INFO - Resuming processing for 3 pending orders
2024-12-15 11:00:00 - INFO - Step 2: Fetching non-canceled payments from Papaya for 3 orders...
...
```

## Bezpieczeństwo

### Najlepsze praktyki

1. **Nigdy nie commituj pliku `.env`** - Plik zawiera wrażliwe dane uwierzytelniające
2. **Nigdy nie commituj plików CSV ze statusem** - Mogą zawierać informacje biznesowe (dodane do .gitignore)
3. **Używaj użytkowników z minimalnymi uprawnieniami** - Dla baz danych używaj kont tylko do odczytu
4. **Zabezpiecz plik `.env`** - Ustaw odpowiednie uprawnienia: `chmod 600 .env`
5. **Regularnie zmieniaj hasła** - Szczególnie dla kont API
6. **Monitoruj logi** - Sprawdzaj logi w poszukiwaniu nieautoryzowanych prób dostępu

### Zabezpieczenia w kodzie

- Parametryzowane zapytania SQL (ochrona przed SQL injection)
- Hasła i tokeny nie są logowane
- Obsługa błędów bez ujawniania wrażliwych informacji
- Połączenia z timeout'ami
- Bezpieczne zamykanie połączeń z bazami danych
- Bezpieczny zapis do plików CSV z kodowaniem UTF-8

## Rozwiązywanie problemów

### Błąd połączenia z bazą danych

```
Failed to connect to database: Can't connect to MySQL server
```

**Rozwiązanie:** Sprawdź parametry połączenia (host, port, użytkownik, hasło) w pliku `.env`

### Błąd uwierzytelnienia API

```
API returned status 401: Unauthorized
```

**Rozwiązanie:** Zweryfikuj dane `PAPAYA_API_LOGIN` i `PAPAYA_API_PASSWORD`

### Błąd formatu daty

```
Invalid date format (expected YYYY-MM-DD)
```

**Rozwiązanie:** Upewnij się, że `DATE_FROM` i `DATE_TO` są w formacie YYYY-MM-DD

### Brak znalezionych zamówień

```
Found 0 canceled orders in Magento
```

**Możliwe przyczyny:**
- Brak anulowanych zamówień w podanym przedziale czasowym
- Nieprawidłowy przedział czasowy
- Brak uprawnień do odczytu danych

### Wszystkie zamówienia już przetworzone

```
No pending orders to process. All orders have been handled.
```

**Wyjaśnienie:** To normalna sytuacja gdy skrypt został już wcześniej uruchomiony i wszystkie zamówienia zostały przetworzone. Plik CSV zawiera kompletną historię przetwarzania.

## Pliki generowane przez skrypt

- **cancel_payments.log** - Szczegółowy log wszystkich operacji
- **payment_cancellation_status_YYYYMMDD_to_YYYYMMDD.csv** - Status przetwarzania zamówień (gdzie YYYYMMDD to daty z konfiguracji)

## Struktura projektu

```
.
├── .env.example          # Przykładowa konfiguracja (szablon)
├── .gitignore           # Pliki ignorowane przez Git
├── README.md            # Dokumentacja projektu
├── requirements.txt     # Zależności Python
└── cancel_payments.py   # Główny skrypt
```

## Zależności

- **python-dotenv** (1.0.0) - Wczytywanie zmiennych środowiskowych z pliku .env
- **pymysql** (1.1.0) - Sterownik bazy danych MySQL/MariaDB dla Python
- **requests** (2.31.0) - Biblioteka HTTP do komunikacji z API

## Licencja

Ten projekt jest udostępniony jako kod źródłowy do użytku wewnętrznego.

## Autor

Piotr Kądziela

## Wsparcie

W przypadku problemów lub pytań:
1. Sprawdź sekcję "Rozwiązywanie problemów" powyżej
2. Przejrzyj plik `cancel_payments.log` w poszukiwaniu szczegółowych informacji o błędach
3. Skontaktuj się z zespołem technicznym