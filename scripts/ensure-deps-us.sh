#!/bin/bash
# Ensure Python + system dependencies for US Stock Picker are installed

# Import-name → pip-install spec (index-matched parallel arrays; bash 3.2-safe,
# so no associative array — macOS /bin/bash is still 3.2).
#
# Polygon + Financial Datasets REST (FD re-instated 2026-08-29, fail-soft, stdlib urllib — no extra dep; cursor-paginated since 2026-09-07); v4.9 (2026-06-09): the data layer is Polygon ("Massive")
# REST/S3 (scripts/uspicks_data.py + uspicks_*_scan.py) — NO yfinance, NO MCP.
# boto3 is REQUIRED for Polygon flat-file (S3) access — the whole-universe
# after-hours close at grading. pandas is floor-pinned to >=2.0 because the price
# scan calls pd.read_html(io.StringIO(...)) for the S&P-500 universe supplement
# (raw-string read_html was deprecated in pandas 2.1) and uses pandas Series for
# the indicators. pytz is used by uspicks_data for the ET after-hours-window
# conversion. lxml/html5lib (read_html parser) + pytz need no pin.
# 2026-07-17: fpdf2 (import name "fpdf") + uharfbuzz power the Phase 7 / U.8
# Arabic weekly PDFs (scripts/uspicks_pdf.py) — uharfbuzz does the RTL
# Arabic text shaping; without it the PDF renders disconnected letters.
REQUIRED_PACKAGES=("boto3" "pandas" "lxml" "html5lib" "pytz" "fpdf" "uharfbuzz")
PIP_SPECS=("boto3" "pandas>=2.0" "lxml" "html5lib" "pytz" "fpdf2" "uharfbuzz")

MISSING_IMPORT=()
MISSING_SPEC=()
idx=0
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING_IMPORT+=("$pkg")
        MISSING_SPEC+=("${PIP_SPECS[$idx]}")
    fi
    idx=$((idx + 1))
done

if [ ${#MISSING_IMPORT[@]} -gt 0 ]; then
    echo "Installing missing packages: ${MISSING_SPEC[*]}"
    # Attempts 1-2 are expected-to-sometimes-fail probes (different install
    # modes); their stderr is suppressed to keep the log clean. The FINAL
    # attempt deliberately does NOT suppress stderr and drops --quiet (T3.4):
    # if every mode fails, the real pip error (resolver conflict, network,
    # PEP-668 externally-managed env, version-pin conflict, etc.) is printed
    # instead of vanishing behind a bare "✗ Failed to install".
    pip3 install --quiet --break-system-packages "${MISSING_SPEC[@]}" 2>/dev/null || \
    pip3 install --quiet "${MISSING_SPEC[@]}" 2>/dev/null || \
    pip3 install --user "${MISSING_SPEC[@]}"

    # Verify installation (by import name; index-matched so the failing spec is
    # echoed for a copy-paste manual retry).
    vidx=0
    for pkg in "${MISSING_IMPORT[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            echo "  ✓ $pkg installed"
        else
            echo "  ✗ Failed to install $pkg (spec: ${MISSING_SPEC[$vidx]})"
            echo "    ↳ See the pip error above. To retry manually:"
            echo "        pip3 install --user '${MISSING_SPEC[$vidx]}'"
            exit 1
        fi
        vidx=$((vidx + 1))
    done
else
    echo "All Python dependencies satisfied."
fi

# Optional: pandoc for /us-picks educate (Phase 5.3 PDF rendering)
# Not a hard requirement — if missing, Phase 5.3 falls back to markdown-only output
if ! command -v pandoc >/dev/null 2>&1; then
    echo ""
    echo "  ℹ️  pandoc not installed (optional)."
    echo "     /us-picks educate will save markdown only (no PDF) until pandoc is present."
    echo "     To enable PDF output: brew install pandoc basictex"
fi
