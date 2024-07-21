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
    """The request contract for the scraping request.

    Attributes:
        pages: An integer indicating the depth of the scraping.
        url: A String which is to be used as the url for the scraping.
    """
    pages:int
    url:str

class Repository:
    """An abstract class providing general methods for persisting data.
    """

    def save_obj(self, obj):
        """Saves the object on the specified system.

        Args:
            obj(any): The object which needs to be saved.
        """
        pass

    def save_image(self, img):
        """Saves the image object on the specified system.

        Args:
            img (any): The image object which needs to be saved.
        """
        pass

class FileSystemRepository(Repository):
    """File system backed repository

    Attributes:
        base_path: A string representing the base path for saving objects and other things
    """

    base_path: str

    def __init__(self, base_path:str) -> None:
        self.base_path = base_path
        super().__init__()

    def save_obj(self, obj):
        """Saves the object specified in the specified filesystem location in the JSON format.

        Args:
            obj (any): An object which needs to be saved.
        """
        path = os.path.join(self.base_path, obj['product_title']+".json")
        obj["path_to_image"] = self.image_path(obj["product_title"])
        with open(path, 'w') as jsonfile:
            json.dump(obj, jsonfile)
    
    def save_image(self, img):
        """Saves the image specified to the filesystem.

        Args:
            img (any): An image object which needs to be saved.
        """
        with open(self.image_path(img['title']), 'wb') as f:
            f.write(img['content'])
    
    def image_path(self, title:str):
        """Computes the image path for the product being saved.

        Args:
            title (str): The String representing the title of the product.

        Returns:
            str: The path of the file system where the image object is saved.
        """
        return os.path.join(self.base_path, title+".jpg")

class ProductGateway:
    """Gateway to retrieve product information.

    Attributes:
        retry_count: An integer representing the number of retries we are to perform should there be any error while getting the response.
        succ_delay: An integer (seconds) representing the the delay between the successive requests in the retry.
    """

    retry_count: int
    succ_delay: int

    def __init__(self, retry_count: int, succ_delay:int) -> None:
        self.retry_count = retry_count
        self.succ_delay = succ_delay
    
    def retrieve(self, url):
        """Retrieves the content on the url.

        Args:
            url (str): A String representing the url to be used for the retrieving the content.

        Returns:
            content : The contents on the specified url.
        """
        response = self.get_response(url)
        return response.content
    
    def get_response(self, url):
        """Gets the response from the url specified

        Args:
            url (str): url which is to be used for making the requests.

        Returns:
            response : Response from the specified url, None if do not able to get anything.
        """
        current_count = 0
        response = None

        while current_count<=self.retry_count and (response==None or response.status_code!=requests.codes.ok):
            if response!=None:
                time.sleep(self.succ_delay)
            response = requests.get(url)
        return response
    
class NotificationService:
    """An abstract notification service
    """

    def notify(self, message: str):
        """Notifies with message passed.

        Args:
            message (str): Message which is to be used for the notification.
        """
        pass

class SimpleConsoleNotificationService(NotificationService):
    """Console notification service.
    """

    def notify(self, message:str):
        """Notifies by printing the message on the console

        Args:
            message (str): The message which is printed on the console 
        """
        print(message)

class CacheService:
    """A simple cache service

    Attributes:
        cache: A symbol table to keep track of the key value pairs
    """
    cache:dict

    def __init__(self) -> None:
        self.cache = {}

    def put(self, key:str, val):
        """Puts the key and value in the dictionary.

        Args:
            key (str): The string key for the symbol table.
            val (any): An object value corresponding to the key.
        """
        self.cache[key] = val
    
    def contains(self, key:str):
        """Checks whether a particular key exists in the cache or not.

        Args:
            key (str): The key for which we need to check.

        Returns:
            bool: Indicating whether the key do exists or not.
        """
        return key in self.cache
    
    def get(self, key:str):
        """Gets the value associated with the key.

        Args:
            key (str): The key to which we want the value.

        Returns:
            value (any): The value associated with the key.
        """
        return self.cache[key]
    
class ProductCacheService(CacheService):
    """Product Cache Service.
    """

    def __init__(self) -> None:
        super().__init__()

    def is_val_diff(self, key:str, val):
        """Checks whether the given val is different with current value associated with the key.

        Args:
            key (str): The key for which we want to check.
            val (any): The new value to which we want to compare.

        Returns:
            bool: Indicates whether the value differs or not.
        """
        return (not self.contains(key)) or self.get(key)!=val

class ScrapeService:
    """Scrapes the Product Information.

    Attributes:
        repository: A Repository where we persist the product information.
        gateway: Gateway through which we send the requests and get the response.
        notification_service: A NotificationService to notify users.
        cache_service: A CacheService, which caches the product details.
    """

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
        """Scrapes the product information.

        Args:
            scrape_request (ScrapeRequest): The request for the scraping.

        Returns:
            int: Number of products updated in the call.
        """
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
        return len(products)
    
    def process_products(self, products_response):
        """Processes the products on a particular page.

        Args:
            products_response (content): Product detail over the page.

        Returns:
            tuple: Product and its corresponding images.
        """

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
        """Removes the special characters from a text.

        Args:
            text (str): String for which the removal of special characters needs to take place.

        Returns:
            str: String without the special characters.
        """
        regex = r"[^\w\s_]"  
        return re.sub(regex, "", text)

# Initializing various components

# The repository
file_system_repository = FileSystemRepository(settings.base_path)
# The gateway
product_gateway = ProductGateway(settings.retry_count, settings.retry_delay)
# The notification service
notification_service = SimpleConsoleNotificationService()
# The product cache
product_cache = ProductCacheService()
# The scraping service (All components DIed into it)
scrape_service = ScrapeService(file_system_repository, product_gateway, notification_service, product_cache)
# The token cache
token_cache = CacheService()
    
app = FastAPI()

@app.post("/scrape/")
async def scrape(scrape_request: ScrapeRequest, token: str = Header(default=None)):
    """Scrapes the information as per the request

    Args:
        scrape_request (ScrapeRequest): The request which contains details about the extent and where to scrape.
        token (str, optional): The token for validating the request.

    Raises:
        HTTPException: When the token is invalid or not provided.

    Returns:
        str: Indicating number of products updated.
    """
    if not validate_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    product_updates = scrape_service.scrape(scrape_request=scrape_request)
    return "{product_updates:"+str(product_updates)+"}"

def validate_token(token:str):
    """Validates the passed against the valid tokens.

    Args:
        token (str): The token which is to be validated.

    Returns:
        bool: Indicating whether the token passed is valid or not.
    """
    return token!=None and token_cache.contains(token)


@app.on_event("startup")
async def startup():
    """Initializes the token cache for all the single digit values.
    """
    for num in range(10):
        token_cache.put(str(num), "User"+str(num))


   