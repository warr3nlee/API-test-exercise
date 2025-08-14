import requests
from bs4 import BeautifulSoup

#Fetch and parse the page

response = requests.get('https://www.geeksforgeeks.org/python/python-programming-language-tutorial/')

#get
#print(response.status_code)
#print(response.content)  # Check if the request was successful

#bs4
soup = BeautifulSoup(response.content, 'html.parser')
#print(soup.prettify())

# Find the main content container
content_div = soup.find('div', class_='article--viewer_content')
if content_div:
    for para in content_div.find_all('p'):
        print(para.text.strip())
else:
    print("No article content found.")