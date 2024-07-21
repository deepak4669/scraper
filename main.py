from fastapi import FastAPI, Header, HTTPException
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
import os
import json
import urllib.parse
import re
import time
from config import settings

class ScrapeRequest(BaseModel):
    pages:int
    url:str


class Repository:

    def save_obj(self, entity, path):
        pass

    def save_image(self, img, path):
        pass

class FileSystemRepository(Repository):

    base_path: str

    def __init__(self, base_path:str) -> None:
        self.base_path = base_path
        super().__init__()

    def save_obj(self, obj):
        path = os.path.join(self.base_path, obj['product_title']+".json")
        obj["path_to_image"] = self.image_path(obj["product_title"])
        with open(path, 'w') as jsonfile:
            json.dump(obj, jsonfile)
    
    def save_image(self, img):
        with open(self.image_path(img['title']), 'wb') as f:
            f.write(img['content'])
    
    def image_path(self, title:str):
        return os.path.join(self.base_path, title+".jpg")

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


class CacheService:
    cache:dict

    def __init__(self) -> None:
        self.cache = {}

    def put(self, key:str, val):
        self.cache[key] = val
    
    def contains(self, key:str):
        return key in self.cache
    
    def get(self, key:str):
        return self.cache[key]
    

    
class ProductCacheService(CacheService):

    def __init__(self) -> None:
        super().__init__()

    def is_val_diff(self, key:str, val):
        return (not self.contains(key)) or self.get(key)!=val



class ScrapeService:

    repository: Repository
    gateway: ProductGateway
    notification_service: NotificationService
    cache_service: CacheService

    def __init__(self, repository: Repository, gateway: ProductGateway, notification_service: NotificationService, cache_service: CacheService) -> None:
        self.repository = repository
        self.gateway = gateway
        self.notification_service = notification_service
        self.cache_service = cache_service

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
        for product in products:
            self.repository.save_obj(product)

        # Save the Images
        for image in product_images:
            self.repository.save_image(image)

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
                current_product_name = self.remove_special_chars(product_image_detail.get("title"))
                current_product_price = product_price_detail

                if not self.cache_service.is_val_diff(current_product_name, current_product_price):
                    continue

                current_product = {}
                current_product['product_title'] = self.remove_special_chars(product_image_detail.get("title"))
                current_product['product_price'] = product_price_detail

                image_url = product_image_detail.get("src")
                current_product_image = {}
                current_product_image['title'] = current_product['product_title']
                current_product_image['content'] = self.gateway.retrieve(image_url)

                products.append(current_product)
                product_images.append(current_product_image)

                self.cache_service.put(current_product_name, current_product_price)
        
        return (products, product_images)

    def remove_special_chars(self, text):
        regex = r"[^\w\s_]"  
        return re.sub(regex, "", text)

file_system_repository = FileSystemRepository(settings.base_path)
product_gateway = ProductGateway(settings.retry_count, settings.retry_delay)
notification_service = SimpleConsoleNotificationService()
product_cache = ProductCacheService()
scrape_service = ScrapeService(file_system_repository, product_gateway, notification_service, product_cache)
token_cache = CacheService()
    
app = FastAPI()

@app.post("/scrape/")
async def scrape(scrape_request: ScrapeRequest, token: str = Header(default=None)):
    if not validate_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scrape_service.scrape(scrape_request=scrape_request)

def validate_token(token:str):
    return token!=None and token_cache.contains(token)


@app.on_event("startup")
async def startup():
    for num in range(10):
        token_cache.put(str(num), "User"+str(num))


   