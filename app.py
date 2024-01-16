import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta,date
from sqlalchemy import and_, or_
import requests
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///offices.db'
app.config['SQLALCHEMY_BINDS'] = {
    'users': 'sqlite:///users.db',
    'vehicles': 'sqlite:///vehicles.db'
}

google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

GOOGLE_CLIENT_ID = '77806323545-mdnu6sacs23dfl0f8h8ps0b6c8ohtggi.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'AIzaSyA2Uc7lRniIj_1LsmOwOCsFt4ZBVV38Xgo'
GOOGLE_REDIRECT_URI = 'http://19070006006se3355final.azurewebsites.net/google-login/callback'


db = SQLAlchemy(app)

class User(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))

class Office(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    rating = db.Column(db.Float, default=0.0)
    num_comments = db.Column(db.Integer, default=0)
    availability_date = db.Column(db.Date)
    amenities = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    map_coordinates = db.Column(db.String(50))

    # Ofisin bir veya birden fazla araca sahip olabilir
    vehicles = db.relationship('Vehicle', back_populates='office', cascade='all, delete-orphan')

    def __init__(self, name, country, city, rating=0.0, num_comments=0, availability_date=None, amenities=None, image_url=None, map_coordinates=None, vehicles=None):
        self.name = name
        self.country = country
        self.city = city
        self.rating = rating
        self.num_comments = num_comments
        self.availability_date = availability_date
        self.amenities = amenities
        self.image_url = image_url
        self.map_coordinates = map_coordinates
        self.vehicles = vehicles or []  # Varsayılan olarak boş bir liste kullan

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    member_discount = db.Column(db.Boolean, default=False)
    special_discount = db.Column(db.Float, default=0.0)
    amenities = db.Column(db.String(255))
    image_url = db.Column(db.String(255))

    # Araç, bir ofise ait olabilir
    office_id = db.Column(db.Integer, db.ForeignKey('office.id'))
    office = db.relationship('Office', back_populates='vehicles')

    def __init__(self, name, price=None, member_discount=False, special_discount=0.0, amenities=None, image_url=None, office=None):
        self.name = name
        self.price = price
        self.member_discount = member_discount
        self.special_discount = special_discount
        self.amenities = amenities
        self.image_url = image_url
        self.office = office



def is_logged_in():
    return 'user_id' in session




def get_user():
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None



@app.route('/')
def home():
    user = get_user()

      
    today = date.today()

    current_saturday = today + timedelta(days=(5 - today.weekday()) % 7)
    current_sunday = current_saturday + timedelta(days=1)

   
    weekend_offices = Office.query.filter(
        Office.availability_date >= current_saturday,
        Office.availability_date <= current_sunday,
        Office.country == user.country if user else True 
    ).order_by(Office.rating.desc()).limit(10).all()

    this_weekend_dates = f"{current_saturday.strftime('%d %B')} - {current_sunday.strftime('%d %B')}"

    return render_template('home.html', offices=weekend_offices, user=user, this_weekend_dates=this_weekend_dates)







@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Giriş başarısız. Lütfen e-posta ve şifrenizi kontrol edin.', 'danger')

    return render_template('login.html')


def is_strong_password(password):
   
    return bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password))


def is_valid_email(email):
    return bool(re.match(r'[^@]+@[^@]+\.[^@]+', email))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():  
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        country = request.form['country']
        city = request.form['city']

       
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return redirect(url_for('register'))

       
        if password != confirm_password:
            return redirect(url_for('register'))

        
        new_user = User(email=email, password=password, first_name=first_name, last_name=last_name, country=country, city=city)

        
        db.session.add(new_user)
        db.session.commit()

       
        flash('Başarıyla kayıt oldunuz. Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))

    return render_template('login.html')



@app.route('/logout')
def logout():
   
    session.pop('user_id', None)
  
    return redirect(url_for('home'))



@app.route('/google-login')
def google_login():
    google_auth_url = f'https://accounts.google.com/o/oauth2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope=email'
    return redirect(google_auth_url)


@app.route('/google-login/callback')
def google_callback():
    auth_code = request.args.get('code')

    if auth_code:
       
        token_url = 'https://accounts.google.com/o/oauth2/token'
        token_data = {
            'code': auth_code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=token_data)
        token_info = response.json()

        if 'access_token' in token_info:
           
            user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
            headers = {'Authorization': f'Bearer {token_info["access_token"]}'}
            user_info_response = requests.get(user_info_url, headers=headers)
            user_info = user_info_response.json()

            
            email = user_info.get('email')
            if email:
                user = User.query.filter_by(email=email).first()

                if user:
                    
                    session['user_id'] = user.id
                    flash('Google ile başarıyla giriş yaptınız!', 'success')
                    return redirect(url_for('home'))
                else:
                    # (rastgele bir şifre atar)
                    import secrets
                    random_password = secrets.token_urlsafe(12)  
                    new_user = User(email=email, password=random_password, first_name=user_info.get('given_name'), last_name=user_info.get('family_name'))
                    db.session.add(new_user)
                    db.session.commit()

                    
                    session['user_id'] = new_user.id
                    flash('Google ile başarıyla kayıt oldunuz ve giriş yaptınız!', 'success')
                    return redirect(url_for('home'))

    flash('Google ile giriş başarısız.', 'danger')
    return redirect(url_for('login'))






@app.route('/search', methods=['POST'])
def search():
    
    city = request.form.get('city')
    date = request.form.get('date')
    guest_count = request.form.get('guest_count')

    
    search_results = perform_search(city, date, guest_count)

   
    user = get_user()

    
    if user:
        return render_template('search.html', search_results=search_results, user=user)

    
    session.pop('user_id', None)
    return render_template('search.html', search_results=search_results)



def perform_search(city, date, guest_count):
   
    filter_conditions = []

    if city:
        filter_conditions.append(Office.city == city)

    if date:
        filter_conditions.append(Office.availability_date == date)

  
    if len(filter_conditions) == 2:
        search_results = Office.query.filter(and_(*filter_conditions)).all()
    else:
      
        search_results = Office.query.filter(or_(*filter_conditions)).all()

    return search_results





@app.route('/office/<int:office_id>')
def office_detail(office_id):
    office = Office.query.get(office_id)

    if not office:
        flash('Ofis bulunamadı!', 'danger')
        return redirect(url_for('home'))

    user = get_user()
    vehicle = office.vehicles[0] if office.vehicles else None 

    return render_template('office_detail.html', office=office, user=user, vehicle=vehicle)




if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()

        if not Office.query.first():
            sample_offices = [
                {"name": "Karşıyaka Şube", "country": "Türkiye", "city": "Karşıyaka", "rating": 8.8, "num_comments": 38,
                 "availability_date": datetime(2024, 1, 20),
                 "amenities": "08:30-18:30 Hizmet Saatleri. 7/24 Whatsapp hattı ve güvenle araç kiralama",
                 "image_url": "office1.jpg", "map_coordinates": "38.470503° N, 27.087576° E"},
                {"name": "Alsancak Şube", "country": "Türkiye", "city": "Alsancak", "rating": 8.7, "num_comments": 13,
                 "availability_date": datetime(2024, 1, 20),
                 "amenities": "08:30-18:30 Hizmet Saatleri. 7/24 Whatsapp hattı ve güvenle araç kiralama",
                 "image_url": "office2.jpg", "map_coordinates": "38.435589° N, 27.140447° E"},
                {"name": "Bornova Şube", "country": "Türkiye", "city": "Bornova", "rating": 9.4, "num_comments": 10,
                 "availability_date": datetime(2024, 1, 21),
                 "amenities": "08:30-18:30 Hizmet Saatleri. 7/24 Whatsapp hattı ve güvenle araç kiralama",
                 "image_url": "office3.jpg", "map_coordinates": "38.454608° N, 27.202493° E"},
            ]

            for office_data in sample_offices:
                office = Office(**office_data)
                db.session.add(office)

            # Bir ofise ait bir araç oluşturuyoruz
            sample_vehicle = Vehicle(
                name="Clio",
                price=1000.0,
                member_discount=False,
                special_discount=0.0,
                amenities="Otomatik",
                image_url="vehicle.jpg"  # Clio'nun resim URL'sini eklemelisiniz
            )
            
            first_office = Office.query.first()

            # Araç ile ofis arasındaki ilişkiyi kuruyoruz
            sample_vehicle.office = first_office

            # Veritabanına ekleyelim
            db.session.add(sample_vehicle)
            db.session.commit()
    
    app.run(debug=True)