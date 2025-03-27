from flask import Flask, request, Response, render_template
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

API_URL = os.getenv("OLLAMA")
if API_URL is None:
    raise ValueError("API_URL environment variable not set.")

def aiget(prompt):
    payload = {"model": "gemma3:4b", "stream": False, "prompt": prompt}

    response = requests.post(API_URL, json=payload)

    return response


def mkpage(desc):
    return aiget(
        f"generate ONLY HTML of a webpage page that's named {desc}. Do NOT include markdown formatting around the HTML, and do NOT use lorem ipsum text, make up believable text instead."
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<path:subpath>")
def proxy(subpath):
    # TODO: make seperate calls for CSS or JS or images

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

        stuff = str(soup)

        return Response(stuff, content_type="text/html")
    else:
        return f"Error: {response.status_code} - {response.text}", response.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
