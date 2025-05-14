from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
from datetime import datetime, timedelta

class ActionFetchDeathTodayFlexible(Action):
    def name(self) -> Text:
        return "action_fetch_death_today"

    def _format_death_message(self, deaths: List[Dict], period: str, lang: str) -> List[str]:
        count = len(deaths)
        details = []

        if lang == "ms":
            period_texts = {
                "today": "hari ini",
                "yesterday": "semalam",
                "this_month": "bulan ini",
                "last_month": "bulan lepas",
                "this_year": "tahun ini",
                "last_week": "minggu lepas"
            }
            time_label = period_texts.get(period, "terkini")
            base_message = f"<b>Terdapat {count} orang meninggal pada {time_label}:</b><br><br>"
            farewell = "Semoga mereka bersemadi dengan aman."
            for idx, record in enumerate(deaths, 1):
                name = record.get("nama", "Tidak diketahui")
                date = record.get("date", "Tarikh tidak tersedia")
                details.append(f"{idx}. {name} meninggal pada {date}<br>")
        else:
            period_texts = {
                "today": "today",
                "yesterday": "yesterday",
                "this_month": "this month",
                "last_month": "last month",
                "this_year": "this year",
                "last_week": "last week"
            }
            time_label = period_texts.get(period, "recently")
            base_message = f"<b>There were {count} people who passed away {time_label}:</b><br><br>"
            farewell = "May they rest in peace."
            for idx, record in enumerate(deaths, 1):
                name = record.get("nama", "Unknown")
                date = record.get("date", "No date")
                details.append(f"{idx}. {name} passed away at {date}<br>")

        # First bubble: count + names
        message_1 = (
            f"{base_message}"
            f"{'<br>'.join(details)}"
        )

        # Second bubble: condolence
        message_2 = (
            f"{farewell}"
        )

        return [message_1, message_2]

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        api_url = "https://kampungkita-lab.apsbcloud.net/api/berita_kematian/all_news"
        auth_token = "Bearer 56|1E8S2NbxX5crU8yVOHZW9wEdvQiiVlBNEDY3CkUs"
        headers = {
            "Authorization": auth_token
        }

        text = tracker.latest_message.get('text', '').lower()

        # Language detection
        if any(word in text for word in ["siapa", "meninggal", "kematian", "senarai", "berita", "hari ini", "semalam", "bulan", "tahun", "minggu", "berapa"]):
            lang = "ms"
        else:
            lang = "en"

        # Period detection
        if any(word in text for word in ["semalam", "yesterday"]):
            period = "yesterday"
        elif any(word in text for word in ["bulan lepas", "last month"]):
            period = "last_month"
        elif any(word in text for word in ["bulan", "this month"]):
            period = "this_month"
        elif any(word in text for word in ["tahun", "year"]):
            period = "this_year"
        elif any(word in text for word in ["minggu", "week", "minggu lepas", "last week"]):
            period = "last_week"
        elif any(word in text for word in ["terkini", "latest", "terbaru", "recent"]):
            period = "latest"
        elif any(word in text for word in ["berapa", "how many"]):
            period = "count"
        else:
            period = "today"

        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()

                berita_results = data.get("berita", [])
                today_results = data.get("bkm_harini", [])
                filtered_results = []

                if period == "today":
                    filtered_results = today_results
                elif period == "yesterday":
                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d %b %Y")
                    filtered_results = [r for r in berita_results if yesterday in r["date"]]
                elif period == "this_month":
                    this_month = datetime.now().strftime("%b %Y")
                    filtered_results = [r for r in berita_results if this_month in r["date"]] + today_results
                elif period == "last_month":
                    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%b %Y")
                    filtered_results = [r for r in berita_results if last_month in r["date"]]
                elif period == "this_year":
                    this_year = datetime.now().strftime("%Y")
                    filtered_results = [r for r in berita_results if this_year in r["date"]] + today_results
                elif period == "last_week":
                    today = datetime.now()
                    last_week_start = today - timedelta(days=today.weekday() + 7)
                    last_week_end = last_week_start + timedelta(days=6)
                    for record in berita_results:
                        try:
                            record_date_str = record["date"].split(",")[0].strip()
                            record_date = datetime.strptime(record_date_str, "%d %b %Y")
                            if last_week_start.date() <= record_date.date() <= last_week_end.date():
                                filtered_results.append(record)
                        except:
                            continue
                elif period == "latest":
                    all_deaths = today_results + berita_results
                    filtered_results = sorted(all_deaths, key=lambda x: x['date'], reverse=True)[:5]
                elif period == "count":
                    filtered_results = today_results
                else:
                    filtered_results = today_results

                # Output
                if filtered_results:
                    if period == "count":
                        count = len(filtered_results)
                        if lang == "ms":
                            dispatcher.utter_message(text=f"Hari ini terdapat {count} orang meninggal.</div>")
                        else:
                            dispatcher.utter_message(text=f"There are {count} people who passed away today.</div>")
                    else:
                        formatted = self._format_death_message(filtered_results, period, lang)
                        for msg in formatted:
                            dispatcher.utter_message(text=msg)
                else:
                    if lang == "ms":
                        dispatcher.utter_message(text="Tiada rekod kematian.")
                    else:
                        dispatcher.utter_message(text="No death records found.")
            else:
                if lang == "ms":
                    dispatcher.utter_message(text=f"Maaf, masalah dengan pelayan: Kod {response.status_code}.")
                else:
                    dispatcher.utter_message(text=f"Sorry, server error with code {response.status_code}.")

        except requests.exceptions.RequestException:
            if lang == "ms":
                dispatcher.utter_message(text="Maaf, tidak dapat menyambung ke pelayan.")
            else:
                dispatcher.utter_message(text="Sorry, could not connect to the server.")

        return []
