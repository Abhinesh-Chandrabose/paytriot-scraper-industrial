Write-Host "[*] Setting up Python environment..." -ForegroundColor Cyan
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host "[+] Setup complete." -ForegroundColor Green
Write-Host "[*] Starting scraper..." -ForegroundColor Cyan
python scraper.py $args
