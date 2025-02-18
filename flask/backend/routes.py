from flask import Blueprint

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return "Hello from Flask with Blueprints!"

@main.route("/about")
def about():
    return "This is the About page"