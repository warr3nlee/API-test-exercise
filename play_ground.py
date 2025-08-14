import requests
from bs4 import BeautifulSoup

response = requests.get('https://www.geeksforgeeks.org/python/python-programming-language-tutorial/')

#get
#print(response.status_code)
#print(response.content)  # Check if the request was successful

#bs4
soup = BeautifulSoup(response.content, 'html.parser')
print(soup.prettify())