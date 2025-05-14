from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

import requests
from datetime import datetime
import random
from rasa_sdk.events import SlotSet, ActiveLoop, EventType
import logging

# Configure logging
logger = logging.getLogger(__name__)

API_URL = "https://kampungkita-lab.apsbcloud.net/api/makanplaces/getallrestaurants/full"  # Replace with your actual URL
AUTH_TOKEN = "Bearer 56|1E8S2NbxX5crU8yVOHZW9wEdvQiiVlBNEDY3CkUs"  # Replace with your actual token

HEADERS = {
    "Authorization": AUTH_TOKEN
}

ALLOWED_AREA = [
    "larkin",
    "johor bahru",
]

ALLOWED_FOOD_TYPE = ["Melayu", "Cina", "India", "mamak", "western"]

# Action to search for a restaurant by name
class ActionSearchRestaurantByName(Action):
    def name(self) -> Text:
        return "action_search_restaurant_by_name"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get user input (case insensitive)
        search_name = next(tracker.get_latest_entity_values("restaurant_name"), None)
        if not search_name:
            dispatcher.utter_message(text="Maaf, saya tidak dapat mencari restoran tanpa nama. Boleh beritahu nama restoran yang anda cari?")
            return []

        search_name_lower = search_name.lower()
        
        try:
            # Call API
            response = requests.get(API_URL, headers=HEADERS, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("list"):
                dispatcher.utter_message(text=f"Maaf, tiada restoran ditemui dengan nama '{search_name}'.")
                return []

            # Find exact or close matches in restaurant names
            matched_restaurants = [
                item["rest_detail"]
                for item in data["list"]
                if search_name_lower in item["rest_detail"]["place_name"].lower()
            ]
            
            if not matched_restaurants:
                dispatcher.utter_message(text=f"Maaf, tiada restoran yang tepat dengan nama '{search_name}'.")
                return []

            # Send header message
            dispatcher.utter_message(text=f"🔍 Hasil carian untuk '{search_name}':")
            
            # Display max 5 results
            for i, rest in enumerate(matched_restaurants[:5], 1):
                message = (
                    f"\n{i}. 🏠 {rest['place_name']}\n"
                    f"   ⭐ Rating: {rest.get('overall_rating', 'N/A')}/5\n"
                    f"   🍽️ Kategori: {', '.join(rest.get('kategori_masakan', ['Tiada info']))}\n"
                    f"   📍 {rest['address']}\n"
                    f"   📞 {rest.get('contact', 'Tiada nombor telefon')}"
                )
                
                if rest.get("media"):
                    dispatcher.utter_message(
                        text=message,
                        image=rest["media"]
                    )
                else:
                    dispatcher.utter_message(text=message)

        except requests.exceptions.RequestException:
            dispatcher.utter_message(text="Maaf, sistem carian restoran sedang sibuk. Sila cuba sebentar lagi.")
        except Exception:
            dispatcher.utter_message(text="Maaf, ada masalah teknikal ketika mencari restoran. Sila cuba lagi nanti.")
        
        return []


# Action to find restaurants by area
class ActionFindRestaurantsNearby(Action):
    def name(self) -> Text:
        return "action_find_restaurants_nearby"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get user input area
        user_area = next(tracker.get_latest_entity_values("area"), None)
        if not user_area:
            dispatcher.utter_message(text="Maaf, saya tidak tahu kawasan mana yang anda maksudkan. Boleh nyatakan kawasan yang anda cari?")
            return []

        user_area_lower = user_area.lower()
        
        try:
            # Call API
            response = requests.get(API_URL, headers=HEADERS, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("list"):
                dispatcher.utter_message(text=f"Maaf, tiada restoran ditemui di kawasan {user_area}.")
                return []

            # Find exact matches in address (case insensitive)
            matched_restaurants = [
                item["rest_detail"] 
                for item in data["list"] 
                if user_area_lower in item["rest_detail"].get("address", "").lower()
            ]
            
            if not matched_restaurants:
                dispatcher.utter_message(text=f"Maaf, tiada restoran yang tepat di kawasan {user_area}.")
                return []

            # Send header message
            dispatcher.utter_message(text=f"🔍 Saya jumpa {min(len(matched_restaurants), 5)} restoran di {user_area}:")

            # Display max 5 results
            for i, rest in enumerate(matched_restaurants[:5], 1):
                message = (
                    f"\n{i}. 🏠 {rest['place_name']}\n"
                    f"   ⭐ Rating: {rest.get('overall_rating', 'N/A')}/5\n"
                    f"   🍽️ Masakan: {', '.join(rest.get('kategori_masakan', ['Tiada info']))}\n"
                    f"   📍 {rest['address']}\n"
                    f"   📞 {rest.get('contact', 'Tiada nombor telefon')}"
                )
                
                if rest.get("media"):
                    dispatcher.utter_message(
                        text=message,
                        image=rest["media"]
                    )
                else:
                    dispatcher.utter_message(text=message)

        except requests.exceptions.RequestException:
            dispatcher.utter_message(text="Maaf, sistem restoran sedang sibuk. Sila cuba sebentar lagi.")
        except Exception:
            dispatcher.utter_message(text="Maaf, ada masalah teknikal. Sila cuba lagi nanti.")
        
        return []


# Action to find open restaurants now
class ActionFindOpenRestaurantsNow(Action):
    def name(self) -> Text:
        return "action_find_open_restaurants_now"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Get current time and day
        current_time = datetime.now().time()
        current_day_en = datetime.now().strftime("%A")  # e.g., "Monday"

        # Map English day names to Malay
        day_map = {
            "Monday": "Isnin",
            "Tuesday": "Selasa",
            "Wednesday": "Rabu",
            "Thursday": "Khamis",
            "Friday": "Jumaat",
            "Saturday": "Sabtu",
            "Sunday": "Ahad",
        }
        current_day_malay = day_map.get(current_day_en, current_day_en)

        # Fetch restaurant data
        response = requests.get(API_URL, headers=HEADERS)

        if response.status_code != 200:
            dispatcher.utter_message(text="Maaf, ada masalah ketika mencari restoran. Sila cuba lagi nanti.")
            return []

        data = response.json()
        open_restaurants = []

        for item in data.get("list", []):
            rest = item["rest_detail"]
            operation_hour = rest.get("operation_hour", {}).get(current_day_malay, "")

            # Skip if closed today
            if operation_hour.lower() == "tutup":
                continue

            # Parse opening and closing times (e.g., "04:30 - 11:30")
            try:
                open_time_str, close_time_str = operation_hour.split(" - ")
                open_time = datetime.strptime(open_time_str, "%H:%M").time()
                close_time = datetime.strptime(close_time_str, "%H:%M").time()

                # Check if current time is within operating hours
                if open_time <= current_time <= close_time:
                    open_restaurants.append(rest)
            except (ValueError, AttributeError):
                # Skip if time format is invalid
                continue

        # Generate response
        if open_restaurants:
            message = "Ini adalah beberapa restoran yang buka sekarang:\n\n"
            for i, rest in enumerate(open_restaurants[:5], 1):
                message += (
                    f"{i}. {rest['place_name']}\n"
                    f"   ⏰ Waktu Operasi: {rest['operation_hour'][current_day_malay]}\n"
                    f"   ☎️ Telefon: {rest['contact']}\n\n"
                )
            dispatcher.utter_message(text=message)
        else:
            dispatcher.utter_message(text="Maaf, tiada restoran yang buka sekarang.")

        return []

# Action to find restaurants by food type
class ActionFindRestaurantsByFoodType(Action):
    def name(self) -> Text:
        return "action_find_restaurants_by_food_type"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        food_type = next(tracker.get_latest_entity_values("food_type"), None)
        
        if not food_type:
            dispatcher.utter_message(text="Maaf, jenis makanan apa yang anda cari? Contoh: Melayu, Cina, Barat, dll.")
            return []
        
        food_type_map = {
            "western": "Masakan Barat",
            "melayu": "Masakan Melayu",
            "cina": "Masakan Cina",
            "india": "Masakan India",
            "mamak": "Masakan India"
        }
        
        kategori = food_type_map.get(food_type.lower(), food_type)
        
        response = requests.get(API_URL, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            matched_restaurants = []
            
            for item in data.get("list", []):
                rest = item["rest_detail"]
                if kategori in rest.get("kategori_masakan", []):
                    matched_restaurants.append(rest)
            
            if matched_restaurants:
                message = f"Berikut adalah restoran dengan masakan {kategori}:\n\n"
                for i, rest in enumerate(matched_restaurants[:5], 1):  # Show max 5 restaurants
                    message += (
                        f"{i}. {rest['place_name']}\n"
                        f"   ⭐ Rating: {rest['overall_rating']}/5\n"
                        f"   📍 Alamat: {rest['address']}\n\n"
                    )
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(text=f"Maaf, saya tidak jumpa restoran dengan masakan {kategori}.")
        else:
            dispatcher.utter_message(text="Maaf, ada masalah ketika mencari restoran. Sila cuba lagi nanti.")
        
        return []

# Action to recommend restaurants
class ActionRecommendRestaurants(Action):
    def name(self) -> Text:
        return "action_recommend_restaurants"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        response = requests.get(API_URL, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            recommended_restaurants = []
            
            for item in data.get("list", []):
                rest = item["rest_detail"]
                if rest.get("recommended", False) or rest.get("overall_rating", 0) >= 5:
                    recommended_restaurants.append(rest)
            
            if recommended_restaurants:
                message = "Berikut adalah beberapa restoran yang saya cadangkan:\n\n"
                for i, rest in enumerate(recommended_restaurants[:5], 1):  # Show max 5 restaurants
                    message += (
                        f"{i}. {rest['place_name']}\n"
                        f"   ⭐ Rating: {rest['overall_rating']}/5\n"
                        f"   🍽️ Kategori: {', '.join(rest['kategori_masakan'])}\n"
                        f"   📍 Alamat: {rest['address']}\n\n"
                    )
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(text="Maaf, saya tidak jumpa restoran yang boleh dicadangkan sekarang.")
        else:
            dispatcher.utter_message(text="Maaf, ada masalah ketika mencari restoran. Sila cuba lagi nanti.")
        
        return []
    

class ActionFindRestaurantsByCategory(Action):
    def name(self) -> Text:
        return "action_find_restaurants_by_category"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Extract category from user input (supports Malay/English)
        restaurant_category = next(tracker.get_latest_entity_values("restaurant_category"), None)
        
        if not restaurant_category:
            dispatcher.utter_message(text="Maaf, saya tidak tahu kategori restoran yang anda cari. Sila nyatakan contoh: Sarapan, Makan Tengahari, Makan Malam, atau 24 Jam.")
            return []

        # Map user input to category IDs (case-insensitive)
        category_map = {
            "sarapan": "1", "breakfast": "1",
            "makan tengahari": "2", "lunch": "2",
            "makan malam": "3", "dinner": "3",
            "24 jam": "4", "24 hours": "4"
        }
        
        # Find matching category ID
        kategori_id = next(
            (v for k, v in category_map.items() if k in restaurant_category.lower()),
            None
        )
        
        if not kategori_id:
            dispatcher.utter_message(text="Maaf, kategori tidak dikenali. Pilihan: Sarapan, Makan Tengahari, Makan Malam, atau 24 Jam.")
            return []

        # Fetch all restaurants (filter locally if API doesn't support it)
        response = requests.get(API_URL, headers=HEADERS)
        
        if response.status_code != 200:
            dispatcher.utter_message(text="Maaf, ada masalah sambungan API. Sila cuba lagi nanti.")
            return []

        data = response.json()
        matching_restaurants = [
            item for item in data.get("list", [])
            if kategori_id in item["rest_detail"].get("kategori_restaurant", [])
        ]

        if not matching_restaurants:
            dispatcher.utter_message(text=f"Saya tak jumpa restoran untuk kategori '{restaurant_category}'.")
            return []

        # Display results (max 5)
        dispatcher.utter_message(text=f"🔍 Saya jumpa {len(matching_restaurants)} restoran untuk '{restaurant_category}':")
        
        for i, item in enumerate(matching_restaurants[:5], 1):
            rest = item["rest_detail"]
            
            # Send text details first
            dispatcher.utter_message(
                text=(
                    f"{i}. {rest['place_name']}\n"
                    f"   ⭐ Rating: {rest['overall_rating']}/5\n"
                    f"   🍽️ Masakan: {', '.join(rest['kategori_masakan'])}\n"
                    f"   📍 Alamat: {rest['address']}\n"
                    f"   ☎️ Telefon: {rest['contact']}"
                )
            )
            
            # Send image separately (if exists)
            if rest.get("media"):
                dispatcher.utter_message(image=rest["media"])

        return []

class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        area = tracker.get_slot("req_area")
        food_type = tracker.get_slot("req_food_type")

        if not area or not food_type:
            dispatcher.utter_message(text="Maklumat kawasan atau jenis makanan tidak lengkap.")
            return []

        # Normalize food_type to match API data
        food_type_map = {
            "western": "Masakan Barat",
            "melayu": "Masakan Melayu",
            "cina": "Masakan Cina",
            "india": "Masakan India",
            "mamak": "Masakan India"
        }
        normalized_food_type = food_type_map.get(food_type.lower(), food_type)

        try:
            response = requests.get(API_URL, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            matched_restaurants = []

            for item in data.get("list", []):
                rest = item.get("rest_detail", {})
                address = rest.get("address", "").lower()
                food_list = rest.get("kategori_masakan", [])

                # Match area and normalized food_type
                if area.lower() in address and any(normalized_food_type.lower() in ft.lower() for ft in food_list):
                    matched_restaurants.append(rest)

            if matched_restaurants:
                selected = random.choice(matched_restaurants)
                name = selected.get("place_name", "Nama tidak diketahui")
                rating = selected.get("overall_rating", 0)
                jenis = ", ".join(selected.get("kategori_masakan", ["Tiada info"]))
                alamat = selected.get("address", "Alamat tidak tersedia")
                contact = selected.get("contact", "Tiada nombor")
                image = selected.get("media")

                message = (
                    f"Saya cadangkan:\n\n"
                    f"🏠 {name}\n"
                    f"⭐ Rating: {rating}/5\n"
                    f"🍽️ Jenis: {jenis}\n"
                    f"📍 {alamat}\n"
                    f"📞 Telefon: {contact}"
                )

                dispatcher.utter_message(text=message)
                if image:
                    dispatcher.utter_message(image=image)
            else:
                dispatcher.utter_message(
                    text=f"Maaf, saya tak jumpa restoran '{normalized_food_type}' di kawasan '{area}'."
                )

        except Exception as e:
            logger.error(f"[ERROR] Restaurant suggestion failed: {str(e)}")
            dispatcher.utter_message(text="Maaf, ada masalah teknikal semasa mencari restoran.")

        return [
            SlotSet("req_area", None),
            SlotSet("req_food_type", None)
        ]

