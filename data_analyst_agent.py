import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

# --- Global Matplotlib Typography & Clean Blue Theme ---
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['font.size'] = 11.0
plt.rcParams['axes.titlesize'] = 14.0
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 11.0
plt.rcParams['axes.labelweight'] = 'normal'
plt.rcParams['xtick.labelsize'] = 10.0
plt.rcParams['ytick.labelsize'] = 10.0
plt.rcParams['legend.fontsize'] = 10.0
plt.rcParams['figure.titlesize'] = 14.0
plt.rcParams['figure.facecolor'] = '#ffffff'
plt.rcParams['axes.facecolor'] = '#ffffff'
plt.rcParams['text.color'] = '#2d3748'
plt.rcParams['axes.labelcolor'] = '#4a5568'
plt.rcParams['xtick.color'] = '#718096'
plt.rcParams['ytick.color'] = '#718096'

# Blue palette constants
BLUE_PRIMARY = '#1a56db'   # Strong blue for main elements
BLUE_DARK = '#1e3a5f'      # Dark navy for bars
BLUE_MID = '#3b82f6'       # Medium blue for secondary elements
BLUE_LIGHT = '#93c5fd'     # Light blue for accents
BLUE_PALE = '#dbeafe'      # Very pale blue for fills
BLUE_LINE = '#2563eb'      # Vibrant blue for lines
LABEL_COLOR = '#1e40af'    # Deep blue for data labels

# --- Helper: Upload Image to FreeImage.host API ---

def upload_to_freeimage_host(filepath: str) -> str:
    """Uploads a local image file to freeimage.host and returns the public HTTPS URL."""
    try:
        if not os.path.exists(filepath):
            return filepath
            
        api_key = "6d207e02198a847aa98d0a2a901485a5"
        url = "https://freeimage.host/api/1/upload"
        
        with open(filepath, "rb") as f:
            res = requests.post(url, data={"key": api_key, "action": "upload"}, files={"source": f})
            
        if res.status_code == 200:
            img_url = res.json().get("image", {}).get("url")
            if img_url:
                print(f"[Image Uploader] Successfully hosted {os.path.basename(filepath)} -> {img_url}")
                return img_url
        print(f"[Image Uploader] Fallback for {filepath}: HTTP {res.status_code}")
        return filepath
    except Exception as e:
        print(f"[Image Uploader] Exception hosting {filepath}: {str(e)}")
        return filepath

# --- Custom API Tools ---

ONLINE_HOUSES = {"Bring a Trailer", "duPont REGISTRY Live", "PCARMARKET", "Car & Classic", "Cars & Bids", "Collecting Cars"}

def get_past_week_six_figure_sales(tool_context: ToolContext, min_price_usd: float = 100000.0, online_only: bool = True) -> dict:
    """Fetches auction sales completed in the past 7 days, filtering specifically for cars >= $100,000 USD from Online Auction platforms (Bring a Trailer, duPont REGISTRY Live, PCARMARKET, etc.)."""
    url = "https://auctions.drgarage.fun:9299/v1/sales"
    api_key = os.getenv("AUCTION_API_KEY", "AucTions")
    headers = {"X-API-Key": api_key}
    auth = ("run", "our-scraper")
    
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    raw_sales = []
    offset = 0
    limit = 200
    
    try:
        while True:
            params = {"since_date": seven_days_ago, "outcome": "sold", "limit": limit, "offset": offset}
            response = requests.get(url, headers=headers, auth=auth, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[Data API Error] HTTP {response.status_code}: {response.text}")
                break
            batch = response.json().get("sales", [])
            if not batch:
                break
            raw_sales.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
    except Exception as e:
        print(f"[Data API Exception] {str(e)}.")

    if not raw_sales:
        print("[Data Analyst] No sales data returned from API.")
        return {
            "status": "no_data",
            "message": "No sales data returned from live auction API for the past 7 days.",
            "total_six_figure_sales_count": 0,
            "total_six_figure_usd_volume": 0.0,
            "six_figure_sales": [],
            "price_band_distribution": {"$100k - $250k": 0, "$250k - $500k": 0, "$500k - $750k": 0, "$750k - $1M": 0, "$1M - $2M": 0, "$2M+": 0},
            "price_band_house_matrix": {},
            "daily_trends_m": {},
            "house_summary": {}
        }
        
    fx_rates = {"GBP": 1.3322, "EUR": 1.1421, "USD": 1.0, "CAD": 0.73, "AUD": 0.65, "JPY": 0.0067}
    
    six_figure_sales = []
    raw_prices_usd = []
    daily_trends = {}
    PRICE_BANDS = [
        "$100k - $250k",
        "$250k - $500k",
        "$500k - $750k",
        "$750k - $1M",
        "$1M - $2M",
        "$2M+"
    ]
    price_bands_past_week = {b: 0 for b in PRICE_BANDS}
    price_band_house_matrix = {b: {} for b in PRICE_BANDS}
    house_summary = {}
    make_summary = {}
    
    for sale in raw_sales:
        price = sale.get("total_price") or sale.get("hammer_price") or 0
        curr = (sale.get("hammer_currency") or "USD").upper()
        rate = fx_rates.get(curr, 1.0)
        price_usd = price * rate
        
        if price_usd >= min_price_usd:
            sale_date = sale.get("sale_date") or "Unknown"
            make = sale.get("make") or "Unknown"
            model = sale.get("model") or ""
            year = sale.get("year") or ""
            house = sale.get("source") or sale.get("event") or "Unknown"
            
            house_lower = house.lower()
            if "pcar" in house_lower:
                house_clean = "PCARMARKET"
            elif "bring" in house_lower or "bat" in house_lower:
                house_clean = "Bring a Trailer"
            elif "sotheby" in house_lower or "rm " in house_lower or "rm_" in house_lower or "rm-" in house_lower or house_lower == "rm" or house_lower.startswith("rm s"):
                house_clean = "RM Sotheby's"
            elif "barrett" in house_lower:
                house_clean = "Barrett-Jackson"
            elif "broad" in house_lower:
                house_clean = "Broad Arrow"
            elif "carandclassic" in house_lower:
                house_clean = "Car & Classic"
            elif "carsandbids" in house_lower:
                house_clean = "Cars & Bids"
            elif "drlive" in house_lower or "dupont" in house_lower:
                house_clean = "duPont REGISTRY Live"
            else:
                house_clean = house.replace("-", " ").title()
                
            if online_only and house_clean not in ONLINE_HOUSES:
                continue
                
            url_link = sale.get("url") or "#"
            photo = sale.get("photo") or ""
            
            item = {
                "year": year,
                "make": make,
                "model": model,
                "vehicle": f"{year} {make} {model}".strip(),
                "price_usd": round(price_usd, 2),
                "original_price": price,
                "currency": curr,
                "auction_house": house_clean,
                "sale_date": sale_date,
                "url": url_link,
                "photo": photo
            }
            six_figure_sales.append(item)
            raw_prices_usd.append(round(price_usd, 2))
            
            # Daily volume accumulator
            if sale_date != "Unknown":
                daily_trends[sale_date] = daily_trends.get(sale_date, 0.0) + price_usd
            
            # Group by 6 requested price bands
            if 100000 <= price_usd < 250000:
                band = "$100k - $250k"
            elif 250000 <= price_usd < 500000:
                band = "$250k - $500k"
            elif 500000 <= price_usd < 750000:
                band = "$500k - $750k"
            elif 750000 <= price_usd < 1000000:
                band = "$750k - $1M"
            elif 1000000 <= price_usd < 2000000:
                band = "$1M - $2M"
            else:
                band = "$2M+"

            price_bands_past_week[band] += 1
            price_band_house_matrix[band][house_clean] = price_band_house_matrix[band].get(house_clean, 0) + 1
                
            # House totals
            if house_clean not in house_summary:
                house_summary[house_clean] = {"volume_usd": 0.0, "count": 0}
            house_summary[house_clean]["volume_usd"] += price_usd
            house_summary[house_clean]["count"] += 1
            
            # Brand (Make) totals
            if make not in make_summary:
                make_summary[make] = {"volume_usd": 0.0, "count": 0}
            make_summary[make]["volume_usd"] += price_usd
            make_summary[make]["count"] += 1

    # Sort all 7-day sales
    six_figure_sales.sort(key=lambda x: x["price_usd"], reverse=True)
    sorted_daily_trends = {k: round(daily_trends[k] / 1e6, 2) for k in sorted(daily_trends.keys())}
    
    # Post-process Averages and Top Brands
    for house in house_summary:
        house_summary[house]["avg_price"] = round(house_summary[house]["volume_usd"] / house_summary[house]["count"], 2)
        
    top_makes = dict(sorted(make_summary.items(), key=lambda item: item[1]['volume_usd'], reverse=True)[:5])
    
    sales_with_photo = [s for s in six_figure_sales if s.get("photo") and s.get("photo").startswith("http")]
    spotlight = sales_with_photo[0] if sales_with_photo else (six_figure_sales[0] if six_figure_sales else None)
    
    # Yesterday / Recent 24h Extraction
    sorted_dates = sorted([k for k in daily_trends.keys() if k != "Unknown"])
    yesterday_date = sorted_dates[-1] if sorted_dates else datetime.now().strftime("%Y-%m-%d")
    
    yesterday_sales = [s for s in six_figure_sales if s.get("sale_date") == yesterday_date]
    if not yesterday_sales and len(sorted_dates) >= 2:
        recent_dates = set(sorted_dates[-2:])
        yesterday_sales = [s for s in six_figure_sales if s.get("sale_date") in recent_dates]
        
    yesterday_sales.sort(key=lambda x: x["price_usd"], reverse=True)
    yesterday_spotlight = next((s for s in yesterday_sales if s.get("photo") and s.get("photo").startswith("http")), yesterday_sales[0] if yesterday_sales else spotlight)
    
    yesterday_house_summary = {}
    for s in yesterday_sales:
        h = s["auction_house"]
        if h not in yesterday_house_summary:
            yesterday_house_summary[h] = {"volume_usd": 0.0, "count": 0}
        yesterday_house_summary[h]["volume_usd"] += s["price_usd"]
        yesterday_house_summary[h]["count"] += 1

    return {
        "period": f"Past 7 Days Rolling (since {seven_days_ago})",
        "filter": "Only cars >= $100,000 USD",
        "total_six_figure_sales_count": len(six_figure_sales),
        "total_six_figure_volume_usd": round(sum(s["price_usd"] for s in six_figure_sales), 2),
        "vehicle_spotlight": spotlight,
        "top_sales_7day": six_figure_sales[:15],
        "top_brands_by_volume": top_makes,
        "raw_prices_usd": raw_prices_usd,
        "daily_trends_m": sorted_daily_trends,
        "price_bands_past_week": price_bands_past_week,
        "price_band_house_matrix": price_band_house_matrix,
        "house_summary_7day_rolling": house_summary,
        "yesterday_focus": {
            "yesterday_date": yesterday_date,
            "yesterday_sales_count": len(yesterday_sales),
            "yesterday_usd_volume": round(sum(s["price_usd"] for s in yesterday_sales), 2),
            "yesterday_spotlight_car": yesterday_spotlight,
            "yesterday_top_movers": yesterday_sales[:10],
            "yesterday_house_summary": yesterday_house_summary
        }
    }

def _get_matrix_or_fetch(tool_context: ToolContext, price_band_house_matrix: dict) -> dict:
    """Helper to ensure price_band_house_matrix is populated with house breakdown dicts."""
    if isinstance(price_band_house_matrix, dict) and any(isinstance(v, dict) for v in price_band_house_matrix.values()):
        return price_band_house_matrix
    try:
        res = get_past_week_six_figure_sales(tool_context)
        if isinstance(res, dict) and "price_band_house_matrix" in res:
            return res["price_band_house_matrix"]
    except Exception:
        pass
    return price_band_house_matrix if isinstance(price_band_house_matrix, dict) else {}


def generate_price_band_chart(tool_context: ToolContext, price_band_house_matrix: dict = None, output_filename: str = "price_band_distribution.png") -> str:
    """Generates a Stacked Bar Chart image (PNG) for the 6 price tiers ($100k-$250k, $250k-$500k, $500k-$750k, $750k-$1M, $1M-$2M, $2M+) with each auction house colored by its share, and returns its public HTTPS URL."""
    try:
        import numpy as np
        bands = ["$100k - $250k", "$250k - $500k", "$500k - $750k", "$750k - $1M", "$1M - $2M", "$2M+"]
        display_labels = ["100k - 250k", "250k - 500k", "500k - 750k", "750k - 1M", "1M - 2M", "2M+"]
        x_pos = np.arange(len(bands))
        
        matrix = _get_matrix_or_fetch(tool_context, price_band_house_matrix)
        is_matrix = isinstance(matrix, dict) and any(isinstance(v, dict) for v in matrix.values())
        
        fig, ax = plt.subplots(figsize=(10, 5.5))
        
        if is_matrix:
            all_houses = set()
            for b in bands:
                if isinstance(matrix.get(b), dict):
                    all_houses.update(matrix[b].keys())
                
            HOUSE_COLORS = {
                "Bring a Trailer": "#2563eb",         # Deep Sapphire Blue
                "duPont REGISTRY Live": "#1e293b",    # Rich Charcoal Slate
                "Cars & Bids": "#d97706",             # Warm Amber Gold
                "Car & Classic": "#059669",           # Emerald Green
                "RM Sotheby's": "#8b0000",            # Crimson Red
                "Broad Arrow": "#7c3aed",             # Royal Purple
                "Barrett-Jackson": "#dc2626",         # Bright Racing Red
                "PCARMARKET": "#0891b2",              # Cyan Teal
                "Collecting Cars": "#ea580c",          # Burnt Orange
                "Hagerty": "#64748b"                  # Slate Grey
            }
            FALLBACK_COLORS = ["#2563eb", "#1e293b", "#d97706", "#059669", "#7c3aed", "#dc2626", "#0891b2", "#ea580c"]
            
            ordered_houses = list(all_houses)
            ordered_houses.sort(key=lambda h: ("Bring" in h, "duPont" in h, "Collecting" in h, "Classic" in h), reverse=True)
            
            bottoms = np.zeros(len(bands))
            for i, house in enumerate(ordered_houses):
                counts = [matrix.get(b, {}).get(house, 0) if isinstance(matrix.get(b), dict) else 0 for b in bands]
                color = HOUSE_COLORS.get(house, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
                ax.bar(x_pos, counts, bottom=bottoms, label=house, color=color, edgecolor='#ffffff', linewidth=0.8, width=0.55)
                bottoms += np.array(counts)
                
            max_total = max(bottoms) if max(bottoms) > 0 else 1
            for i, total in enumerate(bottoms):
                if total > 0:
                    ax.text(i, total + (max_total * 0.02), f"{int(total)}", ha='center', va='bottom', fontsize=11, fontweight='bold', color='#1e3a5f')
            
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(handles, labels, title="Auction House", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False, fontsize=9.5, title_fontsize=10)
        else:
            values = [price_band_house_matrix.get(b, 0) if isinstance(price_band_house_matrix, dict) else 0 for b in bands]
            blues = [BLUE_DARK, BLUE_PRIMARY, BLUE_MID, BLUE_LIGHT, '#60a5fa', '#93c5fd']
            bars = ax.bar(x_pos, values, color=blues[:len(bands)], edgecolor='none', width=0.55)
            max_val = max(values) if values and max(values) > 0 else 1
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + (max_val * 0.02),
                             f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#1e3a5f')
                    
        ax.set_xticks(x_pos)
        ax.set_xticklabels(display_labels, fontsize=10)
        ax.set_title('Past 7 Days: $100K+ Price Tier Volume by Auction House (Stacked)', fontsize=13.5, fontweight='bold', pad=15, color='#1e3a5f')
        ax.set_xlabel('High-End Price Tier (USD)', fontsize=11, labelpad=10)
        ax.set_ylabel('Number of Cars Sold', fontsize=11, labelpad=10)
        ax.grid(axis='y', linestyle='-', alpha=0.12, color='#cbd5e1')
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        filepath = os.path.abspath(output_filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#ffffff')
        plt.close()
        
        public_url = upload_to_freeimage_host(filepath)
        return public_url
    except Exception as e:
        return f"Failed to generate stacked price band chart: {str(e)}"


def generate_histogram_chart(tool_context: ToolContext, price_band_house_matrix: dict = None, output_filename: str = "price_histogram.png") -> str:
    """Generates a 100% Stacked Market Share Percentage Chart image (PNG) showing each auction house's percentage share across the 6 price tiers ($100k-$250k, $250k-$500k, $500k-$750k, $750k-$1M, $1M-$2M, $2M+), and returns its public HTTPS URL."""
    try:
        import numpy as np
        bands = ["$100k - $250k", "$250k - $500k", "$500k - $750k", "$750k - $1M", "$1M - $2M", "$2M+"]
        display_labels = ["100k - 250k", "250k - 500k", "500k - 750k", "750k - 1M", "1M - 2M", "2M+"]
        x_pos = np.arange(len(bands))
        
        matrix = _get_matrix_or_fetch(tool_context, price_band_house_matrix)
        is_matrix = isinstance(matrix, dict) and any(isinstance(v, dict) for v in matrix.values())
        
        fig, ax = plt.subplots(figsize=(10, 5.5))
        
        if is_matrix:
            all_houses = set()
            for b in bands:
                if isinstance(matrix.get(b), dict):
                    all_houses.update(matrix[b].keys())
                
            HOUSE_COLORS = {
                "Bring a Trailer": "#2563eb",         # Deep Sapphire Blue
                "duPont REGISTRY Live": "#1e293b",    # Rich Charcoal Slate
                "Cars & Bids": "#d97706",             # Warm Amber Gold
                "Car & Classic": "#059669",           # Emerald Green
                "RM Sotheby's": "#8b0000",            # Crimson Red
                "Broad Arrow": "#7c3aed",             # Royal Purple
                "Barrett-Jackson": "#dc2626",         # Bright Racing Red
                "PCARMARKET": "#0891b2",              # Cyan Teal
                "Collecting Cars": "#ea580c",          # Burnt Orange
                "Hagerty": "#64748b"                  # Slate Grey
            }
            FALLBACK_COLORS = ["#2563eb", "#1e293b", "#d97706", "#059669", "#7c3aed", "#dc2626", "#0891b2", "#ea580c"]
            
            ordered_houses = list(all_houses)
            ordered_houses.sort(key=lambda h: ("Bring" in h, "duPont" in h, "Collecting" in h, "Classic" in h), reverse=True)
            
            bottoms = np.zeros(len(bands))
            totals = np.array([sum(matrix[b].values()) if isinstance(matrix.get(b), dict) else 0 for b in bands])
            totals_safe = np.where(totals == 0, 1, totals)
            
            for i, house in enumerate(ordered_houses):
                counts = np.array([matrix.get(b, {}).get(house, 0) if isinstance(matrix.get(b), dict) else 0 for b in bands])
                pcts = (counts / totals_safe) * 100.0
                color = HOUSE_COLORS.get(house, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
                ax.bar(x_pos, pcts, bottom=bottoms, label=house, color=color, edgecolor='#ffffff', linewidth=0.8, width=0.55)
                bottoms += pcts
                
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(handles, labels, title="Auction House", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False, fontsize=9.5, title_fontsize=10)
        else:
            values = [price_band_house_matrix.get(b, 0) if isinstance(price_band_house_matrix, dict) else 0 for b in bands]
            blues = [BLUE_DARK, BLUE_PRIMARY, BLUE_MID, BLUE_LIGHT, '#60a5fa', '#93c5fd']
            bars = ax.bar(x_pos, values, color=blues[:len(bands)], edgecolor='none', width=0.55)
            max_val = max(values) if values and max(values) > 0 else 1
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + (max_val * 0.02),
                             f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#1e3a5f')
            
        ax.set_xticks(x_pos)
        ax.set_xticklabels(display_labels, fontsize=10)
        ax.set_title('Past 7 Days: Auction House Market Share by Price Tier (%)', fontsize=13.5, fontweight='bold', pad=15, color='#1e3a5f')
        ax.set_xlabel('High-End Price Tier (USD)', fontsize=11, labelpad=10)
        ax.set_ylabel('Segment Market Share (%)', fontsize=11, labelpad=10)
        ax.set_ylim(0, 105)
        ax.grid(axis='y', linestyle='-', alpha=0.12, color='#cbd5e1')
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        
        filepath = os.path.abspath(output_filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#ffffff')
        plt.close()
        
        public_url = upload_to_freeimage_host(filepath)
        return public_url
    except Exception as e:
        return f"Failed to generate percentage share chart: {str(e)}"

def generate_daily_line_chart(tool_context: ToolContext, daily_trends_m: dict, output_filename: str = "daily_trend_line.png") -> str:
    """Generates a Line Chart image (PNG) showing 7-day high-end volume velocity ($M/day) and returns its public HTTPS URL."""
    try:
        dates = list(daily_trends_m.keys())
        vols = list(daily_trends_m.values())
        
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.fill_between(range(len(dates)), vols, alpha=0.08, color=BLUE_MID)
        ax.plot(dates, vols, marker='o', color=BLUE_LINE, linewidth=2.5, markersize=8,
                markerfacecolor='#ffffff', markeredgecolor=BLUE_LINE, markeredgewidth=2)
        ax.set_title('Past 7 Days: Daily 100K+ USD Market Volume (Millions)', fontsize=14, fontweight='bold', pad=15, color='#1e3a5f')
        ax.set_xlabel('Auction Sale Date', fontsize=11, labelpad=10)
        ax.set_ylabel('Total Spend ($ Millions USD)', fontsize=11, labelpad=10)
        ax.grid(True, linestyle='-', alpha=0.12, color='#cbd5e1')
        for spine in ax.spines.values():
            spine.set_visible(False)
        plt.xticks(rotation=20, ha='right')
        
        for i, txt in enumerate(vols):
            ax.text(dates[i], vols[i] + (max(vols)*0.04 if max(vols)>0 else 0.1),
                    f'${txt:.2f}M', ha='center', va='bottom', fontsize=10, fontweight='bold', color=LABEL_COLOR)
            
        plt.tight_layout()
        filepath = os.path.abspath(output_filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#ffffff')
        plt.close()
        
        public_url = upload_to_freeimage_host(filepath)
        return public_url
    except Exception as e:
        return f"Failed to generate daily line chart: {str(e)}"

def generate_combo_chart(tool_context: ToolContext, house_summary: dict, output_filename: str = "volume_count_combo.png") -> str:
    """Generates a Dual-Axis Combo Chart image (PNG): Bar (Avg Sale Price $K) + Line (Unit Count) sorted by Avg Price descending, and returns its public HTTPS URL."""
    try:
        sorted_houses = sorted(house_summary.items(), key=lambda x: x[1].get("avg_price", 0), reverse=True)
        houses = [h[0].replace('"', '').replace("'", '') for h in sorted_houses]
        avg_prices_k = [h[1]["avg_price"] / 1000.0 for h in sorted_houses]
        counts = [h[1]["count"] for h in sorted_houses]
        
        fig, ax1 = plt.subplots(figsize=(10, 5))
        
        bars = ax1.bar(houses, avg_prices_k, color=BLUE_DARK, edgecolor='none', alpha=0.85, width=0.45, label='Avg Price ($K)')
        ax1.set_ylabel('Average Sale Price ($ Thousands USD)', color=BLUE_DARK, fontsize=11)
        ax1.tick_params(axis='y', labelcolor=BLUE_DARK, labelsize=10)
        ax1.grid(axis='y', linestyle='-', alpha=0.12, color='#cbd5e1')
        for spine in ax1.spines.values():
            spine.set_visible(False)
        plt.xticks(rotation=20, ha='right', fontsize=10)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height + (max(avg_prices_k)*0.02),
                         f'${int(height)}k', ha='center', va='bottom', fontsize=10, fontweight='bold', color=LABEL_COLOR)
        
        ax2 = ax1.twinx()
        ax2.plot(houses, counts, color=BLUE_LINE, marker='o', linewidth=2.5, markersize=8,
                 markerfacecolor='#ffffff', markeredgecolor=BLUE_LINE, markeredgewidth=2, label='Cars Sold')
        ax2.set_ylabel('Number of 6-Figure Lots Sold', color=BLUE_LINE, fontsize=11)
        ax2.tick_params(axis='y', labelcolor=BLUE_LINE, labelsize=10)
        for spine in ax2.spines.values():
            spine.set_visible(False)
        
        ax1.set_title('Past 7 Days: Auction House Ranking by Average Sale Price (USD)', fontsize=14, fontweight='bold', pad=15, color='#1e3a5f')
        fig.tight_layout()
        filepath = os.path.abspath(output_filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#ffffff')
        plt.close()
        
        public_url = upload_to_freeimage_host(filepath)
        return public_url
    except Exception as e:
        return f"Failed to generate combo chart: {str(e)}"

# --- Data Analyst Agent Definition ---

DATA_ANALYST_INSTRUCTION = """You are an expert quantitative Data Analyst focusing EXCLUSIVELY on high-end luxury & collector cars priced at $100,000 USD and above sold on ONLINE AUCTION PLATFORMS, analyzing ONLY past 7-day performance.

CRITICAL DIRECTIVE:
You MUST ONLY query the live API (`get_past_week_six_figure_sales`) and NOTHING ELSE. You must NEVER generate, invent, or use hardcoded simulated/mock sales data.

Your job:
1. Call `get_past_week_six_figure_sales` with online_only=True to fetch real online auction cars sold for >= $100,000 in the past 7 days from the live API.
2. If `status` is "no_data" or no sales are returned from the API:
   - Output an explicit status message: "STATUS: NO_DATA - The live auction API returned no sales data for the past 7 days."
   - Explicitly inform dRew (Editor-in-Chief) that no sales data was returned from the API so dRew can pivot to an upcoming auctions and car collector news issue.
3. If sales ARE returned:
   - Present **YESTERDAY'S PERFORMANCE & KEY HIGHLIGHTS** (`yesterday_focus`):
     * Yesterday's total $100k+ sales count & USD volume.
     * Yesterday's Top Movers table & Spotlight Vehicle candidate.
   - Present **7-DAY ROLLING LEADERBOARD & MACRO METRICS**:
     * 7-day total count & volume.
     * 7-day auction house leaderboard ranked by Average Sale Price.
     * 7-day price band volume distribution.
   - Call ALL 4 graphics generation tools using 7-day rolling metrics to create chart images and retrieve their public HTTPS URLs:
     * `generate_price_band_chart` using price_band_house_matrix (price_band_distribution.png)
     * `generate_histogram_chart` using price_band_house_matrix (price_histogram.png)
     * `generate_daily_line_chart` using daily_trends_m (daily_trend_line.png)
     * `generate_combo_chart` using house_summary (volume_count_combo.png)
   - Pass both **Yesterday's Focus** and the **7-Day Rolling Leaderboard & Chart URLs** to dRew (Editor-in-Chief)."""

data_analyst = Agent(
    name="data_analyst",
    model="gemini-3.6-flash",
    instruction=DATA_ANALYST_INSTRUCTION,
    tools=[
        get_past_week_six_figure_sales,
        generate_price_band_chart,
        generate_histogram_chart,
        generate_daily_line_chart,
        generate_combo_chart
    ]
)