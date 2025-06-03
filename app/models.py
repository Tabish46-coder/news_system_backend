from app import db
from datetime import datetime
class login(db.Model):
    __tablename__ = 'login'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'


class Signup(db.Model):
    __tablename__ = 'Signup'

    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), nullable=False, unique=True)
    Password = db.Column(db.String(255), nullable=False)
    ConfirmPassword = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Signup {self.Name}, {self.Email}>"



class NewsArticle(db.Model):
    __tablename__ = 'news_articles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500))
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    source_name = db.Column(db.String(255))
    url = db.Column(db.Text)
    url_to_image = db.Column(db.Text)
    category = db.Column(db.String(100))
    
    login_id = db.Column(db.Integer, db.ForeignKey('login.id', ondelete='CASCADE'))

    # Relationship (optional, if you want to back-reference from Login)
    login = db.relationship('login', backref=db.backref('articles', cascade='all, delete'), lazy=True)
