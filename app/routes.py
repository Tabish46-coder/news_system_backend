from app import app,db
from flask import jsonify, request
import requests
from datetime import datetime
from sentence_transformers import SentenceTransformer
from deep_translator import GoogleTranslator
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from bs4 import BeautifulSoup
from app.models import login,Signup,NewsArticle
import random
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

VALID_CATEGORIES = {
    "business", "entertainment", "general", "health", "science", "sports", "technology"
}

model = SentenceTransformer('all-MiniLM-L6-v2')
category_embeddings = {
    cat: model.encode(cat) for cat in VALID_CATEGORIES
}

CATEGORY_MAP = {
    "business 💼": "business",
    "entertainment ✨": "entertainment",
    "health 🏥": "health",
    "science 🔬": "science",
    "sports ⚽": "sports",
    "technology 💻": "technology",
    "for you ⭐️": "for_you"   # special handling
}


import random

VALID_CATEGORIES = {
    "business", "entertainment", "general", "health", "science", "sports", "technology"
}

CATEGORY_MAP = {
    "business 💼": "business",
    "entertainment ✨": "entertainment",
    "health 🏥": "health",
    "science 🔬": "science",
    "sports ⚽": "sports",
    "technology 💻": "technology",
    "for you ⭐️": "for_you"   # special handling
}

@app.route("/news", methods=["GET"])
def get_news():
    category_raw = request.args.get("category", "").lower()

    # Map emojis / display names to valid backend categories
    if category_raw in CATEGORY_MAP:
        mapped_category = CATEGORY_MAP[category_raw]
        if mapped_category == "for_you":
            # pick any random valid category if "For You"
            category = random.choice(list(VALID_CATEGORIES))
        else:
            category = mapped_category
    elif category_raw in VALID_CATEGORIES:
        category = category_raw
    else:
        # fallback random if truly invalid
        category = random.choice(list(VALID_CATEGORIES))

    params = {
        "apiKey": "f51ec80138114dda8d7042531bdd733a",
        "category": category,
        "country": "us",      # default to US news
        "pageSize": 10        # number of results to return
    }

    response = requests.get(NEWS_API_URL, params=params, timeout=8)
    return jsonify(response.json()), response.status_code





@app.route("/summarize", methods=["GET"])
def summarize_url():
    url = request.args.get("url")
    if not url:
        return jsonify(error="URL parameter is required"), 400

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return jsonify(error=f"Failed to fetch URL: {str(e)}"), 400

    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    text = '\n'.join(p.get_text() for p in paragraphs).strip()

    if len(text) < 100:
        return jsonify(error="Not enough text content to summarize"), 400

    max_length = 1000
    input_text = text[:max_length]

    try:
        summary_list = app.summarizer(input_text, max_length=150, min_length=40, do_sample=False)
        summary = summary_list[0]['summary_text']
    except Exception as e:
        return jsonify(error=f"Summarization failed: {str(e)}"), 500

    return jsonify(summary=summary)




@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()

    # Check required fields
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({'error': 'Missing required fields'}), 400

    email = data['email']
    password = data['password']

    try:
        user = login.query.filter_by(email=email).first()
        if user and user.password == password:
            # If you have hashed passwords, verify using hash check here instead
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Email and password do not match, try again'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/signup', methods=['POST'])
def signup_user():
    data = request.get_json()

    if not data or not all(k in data for k in ('name', 'email', 'password', 'confirm_password')):
        return jsonify({'error': 'Missing required fields'}), 400

    name = data['name']
    email = data['email']
    password = data['password']
    confirm_password = data['confirm_password']

    
    if password != confirm_password:
        return jsonify({'error': "Passwords don't match"}), 400

    
    existing_user = Signup.query.filter(
        (Signup.Name == name) | (Signup.Email == email)
    ).first()

    if existing_user:
        return jsonify({'error': 'Account with this name or email already exists'}), 409

    try:
        
        new_signup = Signup(
            Name=name,
            Email=email,
            Password=password,           
            ConfirmPassword=confirm_password
        )
        db.session.add(new_signup)

        new_login = login(
            username=name,
            email=email,
            password=password            
        )
        db.session.add(new_login)

        db.session.commit()

        return jsonify({'message': 'User registered successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@app.route('/articles', methods=['POST'])
def add_article():
    data = request.get_json() or {}

    # --- 1. Basic required fields (title & url) --------------------------
    base_required = {'title', 'url'}
    missing = base_required - data.keys()
    if missing:
        return jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400

    # --- 2. Determine login_id from login_id OR email --------------------
    login_id = data.get('login_id')
    email    = data.get('email')

    if not login_id and not email:
        return jsonify(error="Either login_id or email must be provided"), 400

    if login_id:
        login_record = login.query.get(login_id)
        if not login_record:
            return jsonify(error="Invalid login_id"), 404
    else:  # look up by email
        login_record = login.query.filter_by(email=email).first()
        if not login_record:
            return jsonify(error="Email not found"), 404
        login_id = login_record.id

    # --- 3. Parse published_at (optional) --------------------------------
    published_at = None
    if data.get('published_at'):
        try:
            published_at = datetime.fromisoformat(data['published_at'])
        except ValueError:
            return jsonify(error="Invalid published_at format (use ISO-8601)"), 400

    # --- 4. Insert the article ------------------------------------------
    try:
        article = NewsArticle(
            title        = data['title'],
            description  = data.get('description'),
            content      = data.get('content'),
            author       = data.get('author'),
            published_at = published_at,
            source_name  = data.get('source_name'),
            url          = data['url'],
            url_to_image = data.get('url_to_image'),
            category     = data.get('category'),
            login_id     = login_id
        )
        db.session.add(article)
        db.session.commit()

        return jsonify(
            message="Article added successfully",
            article_id=article.id,
            login_id=login_id
        ), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500




@app.route('/articles-by-email', methods=['GET'])
def get_articles_by_email():
    email = request.args.get('email')
    
    # --- 1. Validate email provided ---
    if not email:
        return jsonify(error="Email is required"), 400

    # --- 2. Find login record by email ---
    login_record = login.query.filter_by(email=email).first()
    if not login_record:
        return jsonify(error="Email not found"), 404

    # --- 3. Fetch articles associated with login_id ---
    articles = NewsArticle.query.filter_by(login_id=login_record.id).all()

    if not articles:
        return jsonify(message="No articles found for this user", articles=[]), 200

    # --- 4. Serialize articles ---
    articles_data = []
    for article in articles:
        articles_data.append({
            "id": article.id,
            "title": article.title,
            "description": article.description,
            "content": article.content,
            "author": article.author,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "source_name": article.source_name,
            "url": article.url,
            "url_to_image": article.url_to_image,
            "category": article.category,
            "login_id": article.login_id
        })

    return jsonify(
        message=f"Found {len(articles)} article(s)",
        articles=articles_data
    ), 200




@app.route('/recommend_categories', methods=['GET'])
def recommend_categories():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter is required"}), 400

    user = login.query.filter_by(email=email).first()
    if not user:
        # fallback instead of error
        fallback_categories = ["business", "Entertainment", "Health", "Science", "Sports", "Technology"]
        return jsonify({
            "email": email,
            "recommended_categories": [random.choice(fallback_categories)],
            "similarity_scores": "No user found, fallback category used"
        })

    user_articles = NewsArticle.query.filter_by(login_id=user.id).all()

    # If no articles found → fallback
    if not user_articles:
        fallback_categories = ["business", "Entertainment", "Health", "Science", "Sports", "Technology"]
        return jsonify({
            "email": email,
            "recommended_categories": [random.choice(fallback_categories)],
            "similarity_scores": "No saved articles, fallback category used"
        })

    # Build user profile vector from article title + description
    user_vectors = []
    for article in user_articles:
        text = (article.title or '') + ' ' + (article.description or '')
        if text.strip():
            user_vectors.append(model.encode(text))

    # If no valid content → fallback
    if not user_vectors:
        fallback_categories = ["business", "Entertainment", "Health", "Science", "Sports", "Technology"]
        return jsonify({
            "email": email,
            "recommended_categories": [random.choice(fallback_categories)],
            "similarity_scores": "No valid article content, fallback category used"
        })

    # Compute user profile
    user_profile_vector = np.mean(user_vectors, axis=0)

    # Compute similarity with category vectors
    scores = {
        cat: float(cosine_similarity([user_profile_vector], [cat_vec])[0][0])
        for cat, cat_vec in category_embeddings.items()
    }

    # Get top 3 recommended categories
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    recommendations = [cat for cat, _ in sorted_categories[:3]]

    # Final fallback if similarity failed
    if not recommendations:
        fallback_categories = ["business", "Entertainment", "Health", "Science", "Sports", "Technology"]
        recommendations = [random.choice(fallback_categories)]

    return jsonify({
        "email": email,
        "recommended_categories": recommendations,
        "similarity_scores": scores if scores else "No similarity scores available"
    })



@app.route('/translate_urdu', methods=['GET'])
def translate_to_urdu():
    text = request.args.get('text')
    if not text:
        return jsonify({"error": "Text parameter is required"}), 400

    translated = GoogleTranslator(source='auto', target='ur').translate(text)
    return jsonify({
        "original_text": text,
        "translated_text": translated
    })



@app.route('/update-password', methods=['PUT'])
def update_password():
    data = request.get_json()

    email = data.get('email')
    new_password = data.get('password')

    if not email or not new_password:
        return jsonify({"message": "Email and Password are required"}), 400

    user = Signup.query.filter_by(Email=email).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # Update password fields
    user.Password = new_password
    user.ConfirmPassword = new_password

    db.session.commit()

    return jsonify({"message": "Password updated successfully"}), 200