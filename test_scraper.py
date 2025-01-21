import asyncio
from database import AsyncSessionLocal
from scraper import scrape_all_hospitals

async def main():
    async with AsyncSessionLocal() as session:
        results = await scrape_all_hospitals(session)
        print(f"Scraping completato. Trovati {len(results)} ospedali.")
        for hospital in results:
            print(f"- {hospital.name} ({hospital.department})")

if __name__ == "__main__":
    asyncio.run(main()) 