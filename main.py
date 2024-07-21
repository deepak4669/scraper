from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
import os
import json
import urllib.parse
import re
import time


class ScrapeRequest(BaseModel):
    pages:int
    url:str


class Repository:

    def save_json(self, entity, path):
        pass

    def save_image(self, img, path):
        pass

class FileSystemRepository(Repository):

    def save_json(self, entity, path):
        with open(path, 'w') as jsonfile:
            json.dump(entity, jsonfile)
    
    
    def save_image(self, img, path):
        with open(path, 'wb') as f:
            f.write(img)

class ProductGateway:

    retry_count: int
    succ_delay: int

    def __init__(self, retry_count: int, succ_delay:int) -> None:
        self.retry_count = retry_count
        self.succ_delay = succ_delay
    
    def retrieve(self, url):
        response = self.get_response(url)
        return response.content

    
    def get_response(self, url):
        current_count = 0
        response = None

        while current_count<=self.retry_count and (response==None or response.status_code!=requests.codes.ok):
            if response!=None:
                time.sleep(self.succ_delay)
            response = requests.get(url)
        return response
    
class NotificationService:

    def notify(self, message: str):
        pass

class SimpleConsoleNotificationService(NotificationService):

    def notify(self, message:str):
        print(message)


class ScrapeService:

    repository: Repository
    gateway: ProductGateway
    notification_service: NotificationService

    def __init__(self, repository: Repository, gateway: ProductGateway, notification_service: NotificationService) -> None:
        self.repository = repository
        self.gateway = gateway
        self.notification_service = notification_service

    def scrape(self, scrape_request: ScrapeRequest):
        num_pages = scrape_request.pages
        url = scrape_request.url

        products = []
        product_images = []

        for page_num in range(1, num_pages+1):
            current_url = urllib.parse.urljoin(url, str(page_num))
            current_products_response = self.gateway.retrieve(current_url)
            current_products, current_product_images = self.process_products(current_products_response)
            products.extend(current_products)
            product_images.extend(current_product_images)

        # Save the Products
        products_path = os.path.join(REPOSITORY_PATH, "products.json")
        self.repository.save_json(products, path=products_path)

        # Save the Images
        for image in product_images:
            self.repository.save_image(image['content'], image['path'])

        # Notifying for the update
        self.notification_service.notify("Number of products updated: "+str(len(products)))
    
    def process_products(self, products_response):

        soup = BeautifulSoup(products_response, "html.parser")

        target_class = "products columns-4"
        product_list = soup.find(class_=target_class)

        products = []
        product_images = []

        for product in product_list:
            if type(product)==Tag:
                product_image_detail = product.find_all("img")[1]
                product_price_detail = 0.0
                if product.find("bdi") != None:
                    product_price_detail = float(list(product.find("bdi").children)[1])
                # Name
                current_product = {}
                current_product['product_title'] = product_image_detail.get("title")
                current_product['product_price'] = product_price_detail
                current_product['path_to_image'] = os.path.join(REPOSITORY_PATH, self.remove_special_chars(current_product['product_title']))

                image_url = product_image_detail.get("src")
                current_product_image = {}
                current_product_image['path'] = current_product['path_to_image']
                current_product_image['content'] = self.gateway.retrieve(image_url)

                products.append(current_product)
                product_images.append(current_product_image)
        
        return (products, product_images)

    def remove_special_chars(self, text):
        regex = r"[^\w\s_]"  
        return re.sub(regex, "", text)

file_system_repository = FileSystemRepository()
product_gateway = ProductGateway(3, 3)
notification_service = SimpleConsoleNotificationService()
scrape_service = ScrapeService(file_system_repository, product_gateway, notification_service)
    
app = FastAPI()

REPOSITORY_PATH = '/Users/dpkgyl/scrape_data'

@app.post("/scrape/")
async def scrape(scrape_request: ScrapeRequest):
    
    scrape_service.scrape(scrape_request=scrape_request)



   