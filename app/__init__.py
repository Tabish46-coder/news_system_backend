from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS       # Import CORS
from transformers import pipeline
import config

db = SQLAlchemy()

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

# Enable CORS for all routes and origins
CORS(app)

# Load summarizer model
app.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Import routes and models
from app import models
from app import routes
