import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

#Fetch and parse the page

#response = requests.get('https://www.geeksforgeeks.org/python/python-programming-language-tutorial/')

#get
#print(response.status_code)
#print(response.content)  # Check if the request was successful

#bs4
#soup = BeautifulSoup(response.content, 'html.parser')
#print(soup.prettify())

# Find the main content container
#content_div = soup.find('div', class_='article--viewer_content')
#if content_div:
#    for para in content_div.find_all('p'):
#        print(para.text.strip())
#else:
#    print("No article content found.")

# create webdriver object 
#driver = webdriver.Firefox() 

# get google.co.in 
#driver.get("https://www.google.co.in/ / search?q = geeksforgeeks") 

element_list = []

# Set up Chrome options (optional)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode (optional)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Use a proper Service object
service = Service(ChromeDriverManager().install())

for page in range(1, 3):
    # Initialize driver properly
    driver = webdriver.Chrome(service=service, options=options)

    # Load the URL
    url = f"https://www.riderawrr.com/collection/parts"  #https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=%7Bpage%7D
    driver.get(url)
    time.sleep(2)  # Optional wait to ensure page loads

    # Extract product details
    titles = driver.find_elements(By.CLASS_NAME, "title")
    prices = driver.find_elements(By.CLASS_NAME, "price")
    descriptions = driver.find_elements(By.CLASS_NAME, "description")
    ratings = driver.find_elements(By.CLASS_NAME, "ratings")

    # Store results in a list
    for i in range(len(titles)):
        element_list.append([
            titles[i].text,
            prices[i].text,
            descriptions[i].text,
            ratings[i].text
        ])

    driver.quit()

# Display extracted data
for row in element_list:
    print(row)