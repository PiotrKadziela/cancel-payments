# cancel-payments

Automatyczny skrypt Python do anulowania płatności w systemie Papaya dla zamówień anulowanych w Magento.

## Opis działania

Skrypt wykonuje następujące operacje:

1. **Pobiera anulowane zamówienia z Magento** - Wyszukuje zamówienia anulowane w określonym przedziale czasowym, które mają więcej niż jedną płatność z niepustym identyfikatorem transakcji.

2. **Znajduje nieanulowane płatności w Papaya** - Sprawdza, które płatności powiązane z anulowanymi zamówieniami nie zostały jeszcze anulowane w systemie Papaya.

3. **Anuluje płatności przez API Papaya** - Wysyła żądania anulowania płatności do API Papaya i loguje wyniki operacji.

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

### Przykładowe wyjście

```
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - Starting Payment Cancellation Script
2024-12-15 10:30:00 - INFO - ================================================================================
2024-12-15 10:30:00 - INFO - Configuration loaded successfully for date range: 2024-01-01 to 2024-12-31
2024-12-15 10:30:00 - INFO - Step 1: Fetching canceled orders from Magento...
2024-12-15 10:30:01 - INFO - Connected to database: magento_production
2024-12-15 10:30:02 - INFO - Found 15 canceled orders in Magento
2024-12-15 10:30:02 - INFO - Closed connection to database: magento_production
2024-12-15 10:30:02 - INFO - Step 2: Fetching non-canceled payments from Papaya for 15 orders...
2024-12-15 10:30:02 - INFO - Connected to database: papaya_production
2024-12-15 10:30:03 - INFO - Found 12 non-canceled payments in Papaya
2024-12-15 10:30:03 - INFO - Closed connection to database: papaya_production
2024-12-15 10:30:03 - INFO - Step 3: Canceling 12 payments via Papaya API...
2024-12-15 10:30:04 - INFO - Successfully canceled payment 12345
2024-12-15 10:30:05 - INFO - Successfully canceled payment 12346
...
2024-12-15 10:30:15 - INFO - Cancellation complete: 12 succeeded, 0 failed
2024-12-15 10:30:15 - INFO - ================================================================================
2024-12-15 10:30:15 - INFO - Payment Cancellation Summary:
2024-12-15 10:30:15 - INFO -   Canceled orders found in Magento: 15
2024-12-15 10:30:15 - INFO -   Non-canceled payments found in Papaya: 12
2024-12-15 10:30:15 - INFO -   Payments successfully canceled: 12
2024-12-15 10:30:15 - INFO -   Payments failed to cancel: 0
2024-12-15 10:30:15 - INFO - ================================================================================
2024-12-15 10:30:15 - INFO - Script completed successfully
```

## Bezpieczeństwo

### Najlepsze praktyki

1. **Nigdy nie commituj pliku `.env`** - Plik zawiera wrażliwe dane uwierzytelniające
2. **Używaj użytkowników z minimalnymi uprawnieniami** - Dla baz danych używaj kont tylko do odczytu
3. **Zabezpiecz plik `.env`** - Ustaw odpowiednie uprawnienia: `chmod 600 .env`
4. **Regularnie zmieniaj hasła** - Szczególnie dla kont API
5. **Monitoruj logi** - Sprawdzaj logi w poszukiwaniu nieautoryzowanych prób dostępu

### Zabezpieczenia w kodzie

- Parametryzowane zapytania SQL (ochrona przed SQL injection)
- Hasła i tokeny nie są logowane
- Obsługa błędów bez ujawniania wrażliwych informacji
- Połączenia z timeout'ami
- Bezpieczne zamykanie połączeń z bazami danych

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