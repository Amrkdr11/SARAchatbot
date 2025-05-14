from typing import Text, List, Dict, Any
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import requests
import re
from datetime import datetime

API_URL = "https://kampungkita-lab.apsbcloud.net/api/hebahan/list2"  # Replace with your actual URL
AUTH_TOKEN = "Bearer 56|1E8S2NbxX5crU8yVOHZW9wEdvQiiVlBNEDY3CkUs"  # Replace with your actual token

HEADERS = {
    "Authorization": AUTH_TOKEN
}

class ActionSearchNews(Action):
    def name(self) -> Text:
        return "action_search_news"

    def _clean_query(self, text: str) -> str:
        """Extract search keywords from user message."""
        question_words = [
            'show me', 'any', 'update on', 'what\'s', 'happening in',
            'news about', 'news from', 'tunjukkan', 'berita tentang',
            'ada perkembangan','info', 'apa yang berlaku', 'ada berita'
        ]
        for word in question_words:
            text = re.sub(word, '', text, flags=re.IGNORECASE)
        return re.sub(r'[^\w\s]', '', text).strip().lower()

    def _search_news(self, query: str, news_items: List[Dict]) -> List[Dict]:
        """Find news matching the user's query."""
        matched = []
        query_words = query.split()
        
        for item in news_items:
            search_text = ' '.join([
                str(item.get(field, '')) 
                for field in ["title", "description", "full_desc", "author", "announcer"]
            ]).lower()
            
            if any(word in search_text for word in query_words):
                matched.append(item)
        
        return matched

    def _format_news_message(self, news: Dict) -> str:
        title = news.get("title", "No title")
        date = news.get("publishedAt") or news.get("date", "No date")
        author = news.get("author") or news.get("announcer", "Unknown")
        description = news.get("desc") or news.get("description", "No description provided.")
        url = news.get("url")

        message = (
            f"<b>{title}</b><br>"
            f"<b>Date:</b> {date}<br>"
            f"<b>Author:</b> {author}<br><br>"
            f"<b>Description:</b> {description}"
        )
        
        if url:
            message += f"<br><br><a href='{url}' target='_blank'>Read more</a>"
        
        return message



    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "").strip()
        if not user_message:
            dispatcher.utter_message(text="❗ Please specify a news topic.")
            return []

        search_query = self._clean_query(user_message)
        if not search_query:
            dispatcher.utter_message(text="❗ Couldn't understand your query. Try keywords like 'sports' or 'politics'.")
            return []

        try:
            response = requests.get(API_URL, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            
            # Combine both 'berita' and 'terkini' news
            all_news = data.get("hebahan", {}).get("berita", []) + data.get("hebahan", {}).get("terkini", [])
            matched_news = self._search_news(search_query, all_news)

            if matched_news:
                for news in matched_news[:3]:  # Show top 3 results
                    dispatcher.utter_message(text=self._format_news_message(news))
                
                if len(matched_news) > 3:
                    dispatcher.utter_message(text="ℹ️ More results available.")
            else:
                dispatcher.utter_message(text=f"❌ No news found for '{search_query}'.")

        except requests.RequestException as e:
            dispatcher.utter_message(text="⚠️ News service is temporarily unavailable.")
            print(f"Error fetching news: {str(e)}")
        return []


class ActionDisplayLatestNews(Action):
    def name(self) -> Text:
        return "action_display_latest_news"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:

        try:
            response = requests.get(API_URL, headers=HEADERS)
            response.raise_for_status()
            latest_news = response.json().get("hebahan", {}).get("berita", [])

            if not latest_news:
                dispatcher.utter_message(text="No latest news found.")
                return []

            dispatcher.utter_message(text="🆕 Berita Terkini:")
            for news in latest_news[:3]:  # Show top 3
                dispatcher.utter_message(
                    text=ActionSearchNews()._format_news_message(news))
        except requests.RequestException as e:
            dispatcher.utter_message(text="⚠️ Could not fetch latest news.")
            print(f"Error fetching latest news: {str(e)}")
        return []
    
class ActionDisplayLatestHebahan(Action):
    def name(self) -> Text:
        return "action_display_latest_hebahan"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:

        try:
            response = requests.get(API_URL, headers=HEADERS)
            response.raise_for_status()
            latest_news = response.json().get("hebahan", {}).get("terkini", [])

            if not latest_news:
                dispatcher.utter_message(text="No latest news found.")
                return []

            dispatcher.utter_message(text="🆕 Latest hebahan:")
            for news in latest_news[:3]:  # Show top 3
                dispatcher.utter_message(
                    text=ActionSearchNews()._format_news_message(news))
        except requests.RequestException as e:
            dispatcher.utter_message(text="⚠️ Could not fetch latest news.")
            print(f"Error fetching latest news: {str(e)}")
        return []