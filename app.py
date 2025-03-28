from flask import Flask, request, Response, render_template
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from random import choice
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

API_URL = os.getenv("OLLAMA")
if API_URL is None:
    raise ValueError("API_URL environment variable not set.")

PEXELS_KEY = os.getenv("PEXELS")
if PEXELS_KEY is None:
    raise ValueError("PEXELS_KEY environment variable not set.")

if not os.path.exists("static"):
    os.makedirs("static")

# TODO:
# 1. Use LLM to make a better query? (sometimes the filename isn't actually descriptive)
# 2. Ensure that the image is downloaded, and then modify the LLM generated HTML
#    to actually source the image correctly through flask

def aiget(prompt):
    payload = {"model": "gemma3:4b", "stream": False, "prompt": prompt}

    response = requests.post(API_URL, json=payload)

    return response

def image_get(query):
    try:
        aiq = aiget("Please return a good description to search for an image of " + query).json()['response']
        results = requests.get(f"https://api.pexels.com/v1/search?query={aiq}", headers={"Authorization": PEXELS_KEY})
        photos = results.json()["photos"]
        ranp = choice(photos)
        link = ranp['src']['original']

        # Download the image
        image_response = requests.get(link)
        if image_response.status_code == 200:
            # Extract the file extension from the URL
            file_extension = link.split('.')[-1]
            filename = f"{query.replace(' ', '_')}.{file_extension}"
            filepath = os.path.join("static", filename)

            # Save the image to the /static directory
            with open(filepath, "wb") as f:
                f.write(image_response.content)

            return f"/static/{filename}"
        else:
            print(f"Error downloading image: {image_response.status_code}")
            return "NA"

    except Exception as e:
        print(f"Error fetching image with query '{query}': {e}")
        return "NA"

def mkpage(desc):
    return aiget(
        f"generate ONLY HTML of a webpage page that's named {desc}. Do NOT include markdown formatting around the HTML, and do NOT use lorem ipsum text, make up believable text instead."
    )


@app.route("/")
def index():
    aiq = aiget("Please return ONLY a CSV string of sample search queries that a user might find useful. DO NOT reply with anything else.").json()['response'].replace("```csv","").replace("```" ,"").split(",")
    html = "<ul>"
    bois = aiq
    for l in bois:
        o = l.replace("\"", "")
        html += f"<li><a href='/{o}'>{o}</a></li>"
    html += "</ul>"
    
    return render_template("index.html", links=html)


@app.route("/<path:subpath>")
def proxy(subpath):
    # TODO: how to handle css and js?

    desc = ""
    if "/" in subpath:
        p = subpath.split("/")
        desc = f"{p[0]}, on a subpage {p[1]}"
    else:
        desc = subpath

    response = mkpage(desc)

    if response.status_code == 200:

        stuff = response.json()["response"]

        stuff = stuff.encode("utf-8").decode("unicode_escape")

        if "```html" in stuff:
            stuff = stuff.replace("```html", "").replace("```", "")

        soup = BeautifulSoup(stuff, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"] != "#":
                old_href = a_tag["href"].replace("#", "")
                a_tag["href"] = f"/{subpath}/{old_href}"
            else:
                a_tag["href"] = f"/{subpath}/{a_tag.text.replace('#','').lower()}"

        for a_tag in soup.find_all("a", href=False):
            old_href = a_tag.string
            a_tag["href"] = f"/{subpath}"

        # TODO: find all places where there *should* be images, download them, and update the src 

        stuff = str(soup)

        return Response(stuff, content_type="text/html")
    else:
        return f"Error: {response.status_code} - {response.text}", response.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
