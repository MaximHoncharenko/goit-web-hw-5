import aiohttp
import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any


class ExchangeRateFetcher:
    """
    Клас для отримання курсу валют з публічного API ПриватБанку.
    """
    API_URL = "https://api.privatbank.ua/p24api/exchange_rates?json&date={date}"

    async def fetch_exchange_rate(self, session: aiohttp.ClientSession, date: str) -> Dict[str, Any]:
        """Отримує курс валют на вказану дату."""
        url = self.API_URL.format(date=date)
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise ValueError(f"Помилка отримання даних: {response.status}")
        except Exception as e:
            raise ConnectionError(f"Не вдалося отримати дані з API: {e}")


class ExchangeRateProcessor:
    """
    Клас для обробки курсу валют.
    """
    @staticmethod
    def process_exchange_rates(data: Dict[str, Any], currencies: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Обробляє дані про курс валют та повертає у потрібному форматі."""
        date = data.get("date")
        exchange_rates = data.get("exchangeRate", [])

        processed_data = {date: {currency: {} for currency in currencies}}

        for rate in exchange_rates:
            currency = rate.get("currency")
            if currency in currencies:
                processed_data[date][currency] = {
                    "sale": rate.get("saleRateNB"),
                    "purchase": rate.get("purchaseRateNB")
                }

        return processed_data


class ExchangeRateApp:
    """
    Основний клас програми.
    """
    def __init__(self, fetcher: ExchangeRateFetcher, processor: ExchangeRateProcessor):
        self.fetcher = fetcher
        self.processor = processor

    async def get_exchange_rates(self, days: int, currencies: List[str]) -> List[Dict[str, Any]]:
        """Отримує курс валют за останні кілька днів."""
        if days < 1 or days > 10:
            raise ValueError("Кількість днів повинна бути від 1 до 10.")

        tasks = []
        async with aiohttp.ClientSession() as session:
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y")
                tasks.append(self.fetcher.fetch_exchange_rate(session, date))

            raw_data = await asyncio.gather(*tasks)

        processed_data = [
            self.processor.process_exchange_rates(data, currencies)
            for data in raw_data if data and data.get("exchangeRate")
        ]

        for data in raw_data:
            if not data or not data.get("exchangeRate"):
                date = data.get("date", "Невідома дата") if data else "Невідома дата"
                print(f"Попередження: Дані для дати {date} відсутні або не оновлені.")

        return processed_data


async def main():
    """Точка входу в програму."""
    try:
        if len(sys.argv) < 2:
            print("Використання: py main.py <кількість_днів> [валюти через кому]")
            return

        days = int(sys.argv[1])
        currencies = sys.argv[2].split(",") if len(sys.argv) > 2 else ["EUR", "USD"]

        fetcher = ExchangeRateFetcher()
        processor = ExchangeRateProcessor()
        app = ExchangeRateApp(fetcher, processor)

        rates = await app.get_exchange_rates(days, currencies)
        print(rates)

    except ValueError as e:
        print(f"Помилка: {e}")
    except ConnectionError as e:
        print(f"Мережева помилка: {e}")
    except Exception as e:
        print(f"Непередбачена помилка: {e}")


if __name__ == "__main__":
    if not asyncio.get_event_loop().is_running():
        asyncio.run(main())
    else:
        asyncio.get_event_loop().create_task(main())
