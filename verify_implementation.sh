#!/bin/bash

echo "======================================================================"
echo "Implementation Verification Script"
echo "======================================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: All required files exist
echo -e "\n${YELLOW}[1] Checking required files...${NC}"
files=("cancel_payments.py" ".env.example" ".gitignore" "requirements.txt" "README.md" "test_csv_logger.py" "demo_csv_logger.py")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo "✗ $file missing"
        exit 1
    fi
done

# Check 2: Python syntax
echo -e "\n${YELLOW}[2] Checking Python syntax...${NC}"
if python3 -m py_compile cancel_payments.py test_csv_logger.py demo_csv_logger.py; then
    echo -e "${GREEN}✓${NC} Python syntax check passed"
else
    echo "✗ Python syntax check failed"
    exit 1
fi

# Check 3: Run tests
echo -e "\n${YELLOW}[3] Running test suite...${NC}"
if python3 test_csv_logger.py > /tmp/test_output.log 2>&1; then
    tests_passed=$(grep "Tests completed:" /tmp/test_output.log | grep -o "[0-9]* passed" | grep -o "[0-9]*")
    echo -e "${GREEN}✓${NC} All $tests_passed tests passed"
else
    echo "✗ Tests failed"
    cat /tmp/test_output.log
    exit 1
fi

# Check 4: Check .gitignore
echo -e "\n${YELLOW}[4] Verifying .gitignore...${NC}"
required_ignores=("progress_log.csv" "*.csv" "*.log" "__pycache__/" ".env")
all_good=true
for pattern in "${required_ignores[@]}"; do
    if grep -q "^$pattern" .gitignore; then
        echo -e "${GREEN}✓${NC} .gitignore contains: $pattern"
    else
        echo "✗ .gitignore missing: $pattern"
        all_good=false
    fi
done

if [ "$all_good" = false ]; then
    exit 1
fi

# Check 5: Check .env.example content
echo -e "\n${YELLOW}[5] Verifying .env.example configuration...${NC}"
required_vars=("MAGENTO_DB_HOST" "PAPAYA_DB_HOST" "PAPAYA_API_URL" "PROGRESS_LOG_FILE")
for var in "${required_vars[@]}"; do
    if grep -q "^$var=" .env.example; then
        echo -e "${GREEN}✓${NC} .env.example contains: $var"
    else
        echo "✗ .env.example missing: $var"
        exit 1
    fi
done

# Check 6: Check README documentation
echo -e "\n${YELLOW}[6] Verifying README documentation...${NC}"
required_sections=("CSV" "Status" "Wznawianie" "Konfiguracja")
for section in "${required_sections[@]}"; do
    if grep -qi "$section" README.md; then
        echo -e "${GREEN}✓${NC} README contains section about: $section"
    else
        echo "✗ README missing section: $section"
        exit 1
    fi
done

# Check 7: Check main script features
echo -e "\n${YELLOW}[7] Verifying main script features...${NC}"
required_features=("CSVProgressLogger" "bulk_write_orders" "get_orders_to_process" "STATUS_FETCHED" "STATUS_SUCCESS" "STATUS_ERROR" "STATUS_NO_ACTION")
for feature in "${required_features[@]}"; do
    if grep -q "$feature" cancel_payments.py; then
        echo -e "${GREEN}✓${NC} Main script contains: $feature"
    else
        echo "✗ Main script missing: $feature"
        exit 1
    fi
done

# Check 8: Line counts (basic structure check)
echo -e "\n${YELLOW}[8] Checking file sizes...${NC}"
main_lines=$(wc -l < cancel_payments.py)
readme_lines=$(wc -l < README.md)
test_lines=$(wc -l < test_csv_logger.py)

if [ "$main_lines" -gt 400 ]; then
    echo -e "${GREEN}✓${NC} cancel_payments.py: $main_lines lines (comprehensive)"
else
    echo "✗ cancel_payments.py too short: $main_lines lines"
    exit 1
fi

if [ "$readme_lines" -gt 150 ]; then
    echo -e "${GREEN}✓${NC} README.md: $readme_lines lines (detailed)"
else
    echo "✗ README.md too short: $readme_lines lines"
    exit 1
fi

if [ "$test_lines" -gt 200 ]; then
    echo -e "${GREEN}✓${NC} test_csv_logger.py: $test_lines lines (thorough)"
else
    echo "✗ test_csv_logger.py too short: $test_lines lines"
    exit 1
fi

echo -e "\n======================================================================"
echo -e "${GREEN}All verification checks passed!${NC}"
echo "======================================================================"
exit 0
