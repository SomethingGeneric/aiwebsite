from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

API_URL = "https://ol.mattcompton.dev/api/generate"

@app.route("/<path:subpath>")
def proxy(subpath):
    payload = {
        "model": "llama3.2",
        "stream": False,
        "prompt": f"generate ONLY HTML of a webpage page that's named {subpath}"
    }
    
    response = requests.post(API_URL, json=payload)
    
    if response.status_code == 200:

        stuff = response.json()['response']

        stuff = stuff.encode('utf-8').decode('unicode_escape')

        soup = BeautifulSoup(stuff, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            old_href = a_tag['href']
            a_tag['href'] = f"/{subpath}/{old_href}"

        for a_tag in soup.find_all("a", href=False):
            old_href = a_tag.string
            a_tag['href'] = f"/{subpath}"

        stuff = str(soup)

        return Response(stuff, content_type="text/html")
    else:
        return f"Error: {response.status_code} - {response.text}", response.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
