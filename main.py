from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import httpx, asyncio, base64, os, json, re
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

async def scrape_ebay(query, condition="New"):
    """Scrapes eBay sold listings for average price"""
    cond = '3000' if condition == 'New' else '1000'
    url = f"https://www.ebay.com/sch/i.html?_nkw=lego+{query}&LH_Sold=1&LH_Complete=1&LH_ItemCondition={cond}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers={'User-Agent':'Mozilla/5.0'}, follow_redirects=True)
            soup = BeautifulSoup(r.text, 'html.parser')
            prices = []
            for item in soup.select('.s-item__price')[:15]:
                try:
                    price_text = item.text.split('to')[0]
                    price = float(re.sub(r'[^\d.]', '', price_text))
                    if 1 < price < 10000: prices.append(price)
                except: continue
            avg = round(sum(prices)/len(prices), 2) if prices else None
            return avg, url
    except Exception as e:
        print(f"eBay scrape error: {e}")
        return None, url

async def get_bricklink_image(query, type):
    """Gets BrickLink image URL"""
    prefix = 'S' if type == 'set' else 'M' if type == 'minifigure' else 'P'
    return f"https://img.bricklink.com/ItemImage/{prefix}N/{query}.png"

@app.get("/")
async def root():
    return {"status": "GET BRICKED API Online"}

@app.get("/api/price")
async def get_price(query: str, type: str = "set"):
    """Called when user hits 'Scan Prices' button"""
    ebay_new_task = scrape_ebay(query, "New")
    ebay_used_task = scrape_ebay(query, "Used")
    img_task = get_bricklink_image(query, type)

    (ebay_new, ebay_new_url), (ebay_used, ebay_used_url), img = await asyncio.gather(
        ebay_new_task, ebay_used_task, img_task
    )

    return {
        "query": query,
        "type": type,
        "name": f"LEGO {type.title()} {query}",
        "image": img,
        "sites": [
            {"site":"eBay","condition":"New","price":ebay_new,"link":ebay_new_url},
            {"site":"eBay","condition":"Used","price":ebay_used,"link":ebay_used_url},
            {"site":"BrickLink","condition":"New","price":None,"link":f"https://www.bricklink.com/v2/catalog/catalogitem.page?{type[0].upper()}={query}"},
            {"site":"BrickLink","condition":"Used","price":None,"link":f"https://www.bricklink.com/v2/catalog/catalogitem.page?{type[0].upper()}={query}"}
        ]
    }

@app.post("/api/identify")
async def identify_lego(image: UploadFile = File(...)):
    """Called when user uploads photo"""
    if not OPENAI_KEY:
        return {"error":"OpenAI API key not configured"}
    b64 = base64.b64encode(await image.read()).decode()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={
                "model":"gpt-4o",
                "messages":[{
                    "role":"user",
                    "content":[
                        {"type":"text","text":"Identify this LEGO item. Return ONLY valid JSON: {\"type\":\"set|part|minifigure\",\"id\":\"number\"}. For sets use 5-digit like 75192. For minifigs use sw0001. For parts use 3001."},
                        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}
                    ]
                }],
                "max_tokens":100,
                "temperature":0
            })
        try:
            content = r.json()['choices'][0]['message']['content']
            content = content.strip('`').replace('json','').strip()
            return json.loads(content)
        except Exception as e:
            return {"error": f"Could not parse LEGO ID: {str(e)}"}
