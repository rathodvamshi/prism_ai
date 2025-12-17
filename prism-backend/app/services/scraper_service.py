"""
🕵️‍♂️ DEEP RESEARCH SCRAPER SERVICE

This service handles the heavy lifting: opening the browser, hiding identity, 
blocking ads/images (for speed), and extracting data.

Uses Playwright with stealth mode to bypass bot detection and render JavaScript.
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


async def scrape_dynamic_url(url: str):
    """
    Visits a URL using Headless Chrome, renders JS, and extracts text + main image.
    Optimized for speed by blocking image/font downloads.
    
    Args:
        url: The URL to scrape
        
    Returns:
        dict with keys: source, title, image, content
        None if scraping fails
    """
    print(f"🕵️‍♂️ [Scraper] Diving into: {url}")
    
    async with async_playwright() as p:
        # 1. Launch Browser (Headless for Server)
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]  # Cloud-safe args
        )
        
        # 2. Create Context (Incognito Mode)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = await context.new_page()
        
        # 3. ACTIVATE STEALTH (Bypasses Bot Detection)
        await stealth_async(page)

        # 4. SPEED OPTIMIZATION: Block heavy assets
        # We grab image URLs from HTML tags; we don't need to download the binary files.
        async def route_handler(route):
            resource_type = route.request.resource_type
            if resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", route_handler)

        try:
            # 5. Visit Page & Wait
            # Timeout set to 15s to prevent hanging
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            
            # Tiny wait for dynamic JS (like React/Angular apps)
            await page.wait_for_timeout(2000)

            # 6. Extract Raw HTML
            content = await page.content()
            title = await page.title()
            
            # 7. Extract Main Image (Open Graph / Twitter Card)
            # This is how we get nice images without downloading them
            image_url = await page.get_attribute('meta[property="og:image"]', 'content')
            if not image_url:
                image_url = await page.get_attribute('meta[name="twitter:image"]', 'content')

            # 8. Clean Content with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove junk tags
            for tag in soup(["script", "style", "nav", "footer", "iframe", "svg", "noscript"]):
                tag.decompose()
            
            # Extract clean text
            text = soup.get_text(separator=' ', strip=True)
            # Limit to 3000 chars to fit in LLM Context
            clean_text = " ".join(text.split())[:3000]

            return {
                "source": url,
                "title": title,
                "image": image_url, 
                "content": clean_text
            }

        except Exception as e:
            print(f"❌ [Scraper] Failed on {url}: {e}")
            logger.error(f"Scraping failed for {url}: {e}")
            return None
            
        finally:
            await browser.close()


# Backward compatibility: Keep the old function name for existing code
async def scrape_url(url: str):
    """
    Alias for scrape_dynamic_url for backward compatibility.
    """
    return await scrape_dynamic_url(url)
