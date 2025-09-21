#!/bin/bash
# JavaScript validation script

echo "🔍 Validating JavaScript files..."

# Check syntax
echo "1. Checking syntax..."
for file in static/js/*.js; do
    if node -c "$file" 2>/dev/null; then
        echo "✅ $file - Syntax OK"
    else
        echo "❌ $file - Syntax Error"
        node -c "$file"
        exit 1
    fi
done

# Check for required functions
echo "2. Checking required functions..."
required_functions=(
    "showView"
    "loadSystems"
    "loadDevices"
    "loadConfig"
    "setupEventListeners"
)

for func in "${required_functions[@]}"; do
    if grep -q "function $func\|$func.*function" static/js/app.js; then
        echo "✅ $func - Found"
    else
        echo "❌ $func - Missing"
        exit 1
    fi
done

# Check for balanced braces
echo "3. Checking balanced braces..."
for file in static/js/*.js; do
    open_braces=$(grep -o '{' "$file" | wc -l)
    close_braces=$(grep -o '}' "$file" | wc -l)
    if [ "$open_braces" -eq "$close_braces" ]; then
        echo "✅ $file - Braces balanced ($open_braces pairs)"
    else
        echo "❌ $file - Braces unbalanced (open: $open_braces, close: $close_braces)"
        exit 1
    fi
done

echo "✅ All JavaScript validation passed!"
