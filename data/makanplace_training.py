import requests
import yaml
import os

# API details
API_URL = "https://kampungkita-lab.apsbcloud.net/api/makanplaces/getallrestaurants/full"  # Replace with your actual URL
AUTH_TOKEN = "Bearer 56|1E8S2NbxX5crU8yVOHZW9wEdvQiiVlBNEDY3CkUs"  # Replace with your actual token

# Set up headers with the authorization token
HEADERS = {
    "Authorization": AUTH_TOKEN
}

# Send GET request to the API
response = requests.get(API_URL, headers=HEADERS)

# Check if the response was successful
if response.status_code == 200:
    # Convert response to JSON
    data = response.json()

    # Extract restaurant names
    restaurant_names = []
    for item in data.get("list", []):
        restaurant_name = item["rest_detail"].get("place_name")
        if restaurant_name:
            restaurant_names.append(restaurant_name)

    # Print out the list of restaurant names
    print(restaurant_names)

    # Step 3: Generate Rasa NLU Training Data
    intent_name = "search_restaurant_name_my"
    examples = []

    # Loop through the restaurant names and format them into Rasa examples
    for restaurant in restaurant_names:
        examples.append(f"ada tk kedai makan [{restaurant}](restaurant_name)")
        examples.append(f"kedai makan [{restaurant}](restaurant_name) kt mana?")
        examples.append(f"mana kedai makan [{restaurant}](restaurant_name)?")
        examples.append(f"ada tk restoran [{restaurant}](restaurant_name)")
        examples.append(f"restoran [{restaurant}](restaurant_name) kt mana?")
        examples.append(f"mana restoran [{restaurant}](restaurant_name)?")

    # Path to your existing NLU file
    nlu_file_path = 'chatbot/data/nlu_makan_places.yml'

    # If the NLU file exists, read the existing content
    if os.path.exists(nlu_file_path):
        with open(nlu_file_path, 'r', encoding='utf-8') as file:
            existing_data = yaml.safe_load(file)

        # Append the new examples to the existing NLU data
        new_data = {
            "intent": intent_name,
            "examples": examples  # Correct format: List of examples, not a string
        }

        # Check if 'nlu' key exists in the existing data, otherwise create it
        if 'nlu' not in existing_data:
            existing_data['nlu'] = []

        existing_data['nlu'].append(new_data)
    else:
        # If the NLU file does not exist, create a new structure
        existing_data = {
            "version": "3.1",
            "nlu": [
                {
                    "intent": intent_name,
                    "examples": examples  # Correct format: List of examples
                }
            ]
        }

    # Save the updated NLU data back to the file
    with open(nlu_file_path, 'w', encoding='utf-8') as file:
        yaml.dump(existing_data, file, allow_unicode=True)

    print(f"Training data successfully appended to {nlu_file_path}")

else:
    print("Error fetching data from API:", response.status_code)
