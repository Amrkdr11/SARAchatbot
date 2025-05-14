from typing import Text, List, Dict, Any
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import requests
import re


API_URL = " https://kampungkita-lab.apsbcloud.net/api/jualbeli/list" 
AUTH_TOKEN = "Bearer 56|1E8S2NbxX5crU8yVOHZW9wEdvQiiVlBNEDY3CkUs"  

HEADERS = {
    "Authorization": AUTH_TOKEN
}

class ActionSearchItem(Action):
    def name(self) -> Text:
        return "action_search_item"
    
    def _clean_query(self, text: str) -> str:
        """Remove common question words and phrases to get the core search term."""
        question_words = [
            'ada jual', 'ada barang', 'nak beli', 'nk beli', 'jual', 'beli', 'x ada'
        ]

        # Remove intent triggers
        for word in question_words:
            text = re.sub(word, '', text, flags=re.IGNORECASE)

        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', '', text).strip()
        return text.lower()
    
    def _format_item_message(self, item: Dict) -> str:
        """Format the item information into a nicely structured message with HTML."""
        name = item.get("name", "Tiada nama")
        price = item.get("price", "Tiada harga")
        phone = item.get("phone_no", "Tiada nombor telefon")
        desc = item.get("desc", "Tiada deskripsi")
        item_type = self._get_type_name(item.get("type", 0))
        created_at = item.get("created_at", "Tiada maklumat tarikh")
        
        message = (
            f"<b>{name}</b><br><br>"
            f"💰 Harga: RM{price}<br>"
            f"📞 Telefon:{phone}<br>"
        )
        
        return message
    
    def _get_type_name(self, type_id: int) -> str:
        """Convert type ID to human-readable name."""
        type_map = {
            1: "makanan",
            2: "barangan",
            3: "perkhidmatan"
        }
        return type_map.get(type_id, "unknown")
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        # Get user message and clean it
        user_message = tracker.latest_message.get("text", "").strip()
        
        if not user_message:
            dispatcher.utter_message(text="❗ Sila beritahu saya barang apa yang anda cari.")
            return []
        
        # Clean the query to get search terms
        search_query = self._clean_query(user_message)
        if not search_query:
            dispatcher.utter_message(text="❗ Saya tidak faham barang apa yang anda cari. Sila cuba lagi.")
            return []
        
        try:
            # Fetch item data 
            response = requests.get(API_URL, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            all_items = data.get("items", [])
            
            if not all_items:
                dispatcher.utter_message(text="⚠️ Tiada item tersedia buat masa ini.")
                return []

            # Get cleaned query words for matching
            query_words = search_query.split()
            
            # Enhanced search with multiple matching criteria
            matched_items = []
            for item in all_items:
                if item.get('status', 0) != 1:  # Skip inactive items
                    continue
                    
                # Prepare all searchable text fields
                name = item.get("name", "").lower()
                desc = item.get("desc", "").lower()
                item_type = self._get_type_name(item.get("type", 0)).lower()
                
                # Calculate match score
                score = 0
                
                # 1. Exact matches get highest priority
                exact_name_match = any(word == name for word in query_words)
                exact_desc_match = any(word == desc for word in query_words)
                
                if exact_name_match:
                    score += 10
                if exact_desc_match:
                    score += 5
                    
                # 2. Partial matches in name
                name_matches = sum(1 for word in query_words if word in name)
                score += name_matches * 3
                
                # 3. Partial matches in description
                desc_matches = sum(1 for word in query_words if word in desc)
                score += desc_matches
                
                # 4. Type matches
                type_matches = sum(1 for word in query_words if word in item_type)
                score += type_matches * 2
                
                # 5. Recent items get slight boost
                created_at = item.get("created_at", "")
                if "hari" in created_at or "hari" in created_at:
                    score += 1
                
                if score > 0:
                    matched_items.append({
                        "item": item,
                        "score": score,
                        "exact_match": exact_name_match or exact_desc_match
                    })

            # Sort results
            matched_items.sort(
                key=lambda x: (
                    -x['exact_match'],
                    -x['score'],
                    x['item'].get('created_at', '')
                )
            )
            
            # Extract just the items after sorting
            sorted_items = [match['item'] for match in matched_items]

            if sorted_items:
                # Send top 3 most relevant results
                for item in sorted_items[:3]:
                    formatted_message = self._format_item_message(item)
                    image_url = item.get("image", "")
                    
                    # Try to send image if available
                    try:
                        if image_url and image_url.startswith('http'):
                            dispatcher.utter_message(
                                text=formatted_message,
                                image=image_url,
                                parse_mode="HTML"
                            )
                        else:
                            dispatcher.utter_message(
                                text=formatted_message,
                                parse_mode="HTML"
                            )
                    except Exception as e:
                        print(f"Error sending image: {e}")
                        dispatcher.utter_message(
                            text=formatted_message,
                            parse_mode="HTML"
                        )

                # Show "more results" message if applicable
                if len(sorted_items) > 3:
                    dispatcher.utter_message(
                        text=f"ℹ️ Ada <b>{len(sorted_items)-3}</b> hasil lagi yang mungkin relevan di bahagian jual beli",
                        parse_mode="HTML"
                    )
            else:
                dispatcher.utter_message(
                    text=f"❌ Tiada item dijumpai untuk '<b>{search_query}</b>'. Cuba kata kunci lain.",
                    parse_mode="HTML"
                )

        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(text="⚠️ Gagal menyambung ke pelayan. Sila cuba lagi nanti.")
            print(f"API request failed: {str(e)}")
        except Exception as e:
            dispatcher.utter_message(text="⚠️ Terdapat ralat dalam sistem. Sila cuba lagi.")
            print(f"Unexpected error: {str(e)}")

        return []