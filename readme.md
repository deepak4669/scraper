# Scraper
A simple application written in Python to scrape product information from  [this](https://dentalstall.com/shop/) website. The implementation uses [Fast API](https://fastapi.tiangolo.com/) as the web framework and [Beautiful Soup](https://beautiful-soup-4.readthedocs.io/en/latest/) for parsing the HTML. The parsed content is stored on the local filesystem.

## Running it Locally
All the dependencies of the application are specified in the requirements.txt of the project, after cloning it run the below to install them.

```bash
pip install -r requirements.txt
```
The `config.py` specified the configurations required for the application. Since the parsed data is stored on the local filesystem, it's imperative that we set `base_path` to some place in our system where we'd like those files.
```python
base_path:str = # set to some place in the local filesystem
```
Run the application by the below:
```bash
fastapi dev main.py
```
Once the application use the specification to send requests to it.
### Specifications
Specifications can be found [here](http://127.0.0.1:8000/docs) locally.

### Sample Request
A sample request to test the application is given below:
```json
{
    "pages":1,
    "url":"https://dentalstall.com/shop/1"
}
```
### Token Header
The application uses very simple authorization check where in one has to specify a single number in `token` header while sending the request.

# Note
The application is written quickly for the indicative purposes and should not be considered as final implementation.



