Trying to make a computer algorithm that optimizes a career fair layout

### End-to-end from a layout image or PDF

1) Install deps: `pip install -r requirements.txt` (pdf2image + poppler needed for PDFs).
2) Run:  
   `python3 run_from_image.py --image Layout.png --pop-file Career_Fair_Recruiting_Popularity.xlsx --plot-file layout_from_image.png`  
   - For PDFs: `--image Layout.pdf` (needs poppler).  
   - Coordinates extracted to `detected_layout.xlsx`; the optimizer runs automatically and saves a plotted layout.
3) Optional: keep a debug detection image with `--debug-image debug.png` to see OCR boxes.

### Build popularity scores from market cap
- Ensure `tickers.csv` exists in the repo with columns `company_name,ticker`.
- Install deps: `pip install -r requirements.txt` (needs network to fetch from Yahoo via yfinance).
- Run: `python3 build_popularity_from_market_cap.py`
- Output: `companies.csv` with columns `company_name,ticker,market_cap,popularity_score` (popularity = market cap; 0 if missing/failed).
