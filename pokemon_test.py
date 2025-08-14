import requests

url = "https://pokeapi.co/api/v2/pokemon?limit=10"

response = requests.get(url)
response.raise_for_status()
data = response.json()

for item in data["results"]:
    name = item["name"]
    detail_res = requests.get(item["url"])
    detail_res.raise_for_status()
    detail_data = detail_res.json()

    base_experience = detail_data["base_experience"]
    print(f"{name} — Base Experience: {base_experience}")