# GET BRICKED Price Scanner API

Backend for LEGO price scanner. Scrapes eBay sold listings + BrickLink images.

### Endpoints:
- `GET /api/price?query=75192&type=set` — Returns eBay + BrickLink prices
- `POST /api/identify` — Identifies LEGO from photo using OpenAI Vision

### Deploy to Railway:
1. Add `OPENAI_API_KEY` in Variables
2. Deploy from this repo
