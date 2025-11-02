from flask import Flask, render_template, request, jsonify, session, redirect, url_for,json, flash
from flask_sqlalchemy import SQLAlchemy
import os
import pandas as pd
from werkzeug.utils import secure_filename
import re
from utils.text_utils import find_best_place_match
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
app = Flask(__name__)
app.secret_key = 'x!7R$ecretK3y2025'

# إعداد قاعدة البيانات (SQLite افتراضيًا، تقدر تغيرها لـ MySQL أو PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///places.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@app.route('/set-language', methods=['POST'])
def set_language():
    lang = request.form.get('lang', 'en')
    session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

# ========== تعريف الموديل ==========
class Place(db.Model):
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(100), unique=True, nullable=False)
    name_place = db.Column(db.String(200), nullable=False)
    place_type = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    link_photo = db.Column(db.String(500), nullable=True)
    lat = db.Column(db.String(50), nullable=True)
    lng = db.Column(db.String(50), nullable=True)
    iframe_url = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    link_pa = db.Column(db.String(200), nullable=True)
    details_url = db.Column(db.String(200), nullable=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(100), nullable=False)
# إنشاء الجداول
with app.app_context():
    db.create_all()

# ================== Routes ==================

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/place/<name>')
def show_place(name):
    short_name = name.lower().replace(" ", "_")
    place = Place.query.filter_by(short_name=short_name).first()
    if not place:
        return f"❌ المكان غير موجود: {short_name}", 404
    return render_template("place.html", place=place)

@app.route('/admin/<name>')
def show_admin_place(name):
    short_name = name.lower().replace(" ", "_")
    place = Place.query.filter_by(short_name=short_name).first()
    if not place:
        return f"❌ المكان غير موجود: {short_name}", 404
    return render_template("admin_place.html", place=place, place_key=short_name)

@app.route("/place_dash")
def place_dash():
    places = Place.query.all()
    places_list = [
        (p.link_photo, p.short_name, p.link_pa, p.details_url, p.description)
        for p in places
    ]
    return render_template("place_dash.html", place=places_list)
@app.route('/info')
def info():
    places = Place.query.all()
    number_of_places = len(places)
    
    places_list = [
        (p.link_photo, p.short_name, p.link_pa, p.details_url, p.description,p.city,p.place_type)
        for p in places
    ]
    return render_template('info.html', place=places_list, number_of_places=number_of_places)

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/users_dash")
def users_dash():
    users = User.query.all()
    users_list = [
        (u.username, u.email, u.phone, u.address)
        for u in users
    ]
    return render_template("users_dash.html", users=users_list)

# ================== User Add Place ==================

REQUEST_FILE = "user_place_requests.json"


# ============== User Add Place (طلب المستخدم) ==============
@app.route("/add_place_from_user", methods=["GET", "POST"])
def add_place_from_user():
    if request.method == "POST":
        name_place = request.form.get("name_place", "").strip()
        short_name = name_place.lower().replace(" ", "_")
        place_type = request.form.get("place_type", "").strip()
        city = request.form.get("city", "").strip()
        lat = request.form.get("lat", "").strip()
        lng = request.form.get("lng", "").strip()
        link_photo = request.form.get("link_photo", "").strip()
        description = request.form.get("description", "").strip()
        iframe_url = request.form.get("iframe_url", "").strip()

        # حفظ الطلب في ملف JSON (كمؤقت)
        new_request = {
            "name_place": name_place,
            "short_name": short_name,
            "place_type": place_type,
            "city": city,
            "lat": lat,
            "lng": lng,
            "link_photo": link_photo,
            "description": description,
            "iframe_url": iframe_url,
        }

        if os.path.exists(REQUEST_FILE):
            with open(REQUEST_FILE, "r", encoding="utf-8") as f:
                requests_data = json.load(f)
        else:
            requests_data = []

        requests_data.append(new_request)

        with open(REQUEST_FILE, "w", encoding="utf-8") as f:
            json.dump(requests_data, f, ensure_ascii=False, indent=4)

        return render_template("add_place_from_user.html", success="✅ تم إرسال طلبك بنجاح!")

    return render_template("add_place_from_user.html")


# ============== Admin View Requests (الإدمن يشوف الطلبات) ==============
@app.route("/request_place")
def request_place():
    if os.path.exists(REQUEST_FILE):
        with open(REQUEST_FILE, "r", encoding="utf-8") as f:
            requests_data = json.load(f)
    else:
        requests_data = []

    return render_template("request_place.html", requests=requests_data)


@app.route("/handle_place_request", methods=["POST"])
def handle_place_request():
    short_name = request.form.get("short_name")
    action = request.form.get("action")

    # قراءة كل الطلبات من الملف
    if os.path.exists(REQUEST_FILE):
        with open(REQUEST_FILE, "r", encoding="utf-8") as f:
            requests_data = json.load(f)
    else:
        requests_data = []

    # نبحث عن الطلب المطلوب حسب short_name
    target_request = next((r for r in requests_data if r["short_name"] == short_name), None)

    if not target_request:
        flash("❌ الطلب غير موجود!", "error")
        return redirect(url_for("request_place"))

    if action == "accept":
        # حفظ الطلب في قاعدة البيانات
        new_place = Place(
            name_place=target_request["name_place"],
            name_country=target_request["city"],
            description=target_request["description"],
            lat=float(target_request["lat"]) if target_request["lat"] else None,
            lng=float(target_request["lng"]) if target_request["lng"] else None,
        )
        db.session.add(new_place)
        db.session.commit()

        flash(f"✅ تم قبول المكان: {target_request['name_place']}", "success")

    elif action == "reject":
        flash(f"🚫 تم رفض المكان: {target_request['name_place']}", "info")

    # حذف الطلب من القائمة
    requests_data = [r for r in requests_data if r["short_name"] != short_name]
    with open(REQUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(requests_data, f, ensure_ascii=False, indent=4)

    return redirect(url_for("request_place"))

# ================== ChatBot ==================
user_state = {
    "location": "",
    "lookingFor": None,
    "selected_place": None
}
def predict_intent(text):
    """
    Simple AI intent prediction (تحديد النية من الكلام)
    """
    text = text.lower()

    if any(word in text for word in ["hi", "hello", "hey", "سلام", "اهلا"]):
        return "greeting"
    elif any(word in text for word in ["thanks", "thank you", "thx", "شكرا"]):
        return "thanks"
    elif any(word in text for word in ["bye", "goodbye", "مع السلامه", "سلام"]):
        return "goodbye"
    elif any(word in text for word in ["how are you", "عامل ايه", "ازيك", "اخبارك"]):
        return "smalltalk"
    else:
        return "unknown"


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    response, iframe = process_input(user_input)
    return jsonify({"response": response, "iframe": iframe})
def process_input(user_input):
    global user_state
    response = "❓ I'm not sure I understand that."
    iframe = ""

    user_input_clean = user_input.strip().lower()

    # --- Step 1: AI intent detection ---
    intent = predict_intent(user_input_clean)

    if intent == "greeting":
        return "👋 Hello! How can I help you today?", ""

    elif intent == "thanks":
        return "😊 You're welcome!", ""

    elif intent == "goodbye":
        return "👋 Goodbye! Have a great day!", ""

    elif intent == "smalltalk":
        return "🤖 I'm doing great, thanks for asking!", ""

    # --- Step 2: Fuzzy match with all places ---
    places = Place.query.all()
    best_match, score = find_best_place_match(user_input_clean, places)

    if best_match and score >= 70:
        iframe = iframe_to_html(best_match.iframe_url)
        response = f"📍 {best_match.name_place} ({best_match.city}, {best_match.place_type})\n\n{best_match.description or ''}"
        return response, iframe

    # --- Step 3: Keyword-based fallback (if fuzzy fails) ---
    def match(pattern):
        return re.search(pattern, user_input_clean, re.IGNORECASE)

    if match(r'\b(hospital|hotel|bank|school)s?\b'):
        found_type = match(r'\b(hospital|hotel|bank|school)s?\b').group(1).lower()
        filtered = [p for p in places if found_type in p.place_type.lower()]
        if filtered:
            place_list = "\n".join([f"- {p.name_place}" for p in filtered[:5]])
            response = f"🔍 Found {found_type}s:\n{place_list}"
        else:
            response = f"❌ No {found_type}s found."
    else:
        response = "🧠 Try asking about a specific place or type like 'hotel' or 'bank'."

    return response, iframe

def iframe_to_html(iframe_code):
    return iframe_code or ""


@app.route('/signup')
def signup():    return render_template("user_sign.html")

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('conf_pass', '').strip()
    if password != confirm_password:
        return render_template("user_sign.html", error="❗كلمة المرور غير متطابقة.", form=request.form)
    if User.query.filter((User.username == username) | (User.email == email) | (User.phone == phone)).first():
        return render_template("user_sign.html", error="❗المستخدم موجود مسبقًا.", form=request.form)

    new_user = User(
        username=username,
        email=email,
        phone=phone,
        address=address,
        password=password
    )
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login_user'))

@app.route('/login_user')
def login_user():
    return render_template("login_user.html")

@app.route('/login_user_act', methods=['POST'])
def login_user_act():
    username_or_email = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    user = User.query.filter(
        ((User.username == username_or_email) | (User.email == username_or_email)) &
        (User.password == password)
    ).first()
    if user:
        session['user_logged_in'] = True
        session['username'] = user.username
        return redirect(url_for('home'))
    else:
        return render_template("login_user.html", error="❗بيانات الدخول غير صحيحة.")
@app.route('/logout_user')
def logout_user():
    session.pop('user_logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))    
@app.route('/map')
def map():
    places = Place.query.all()
    landmarks = [
        {
            "lat": p.lat,
            "lng": p.lng,
            "name_place": p.name_place,
            "url": p.short_name,
            "size": 0.3
        }
        for p in places
    ]
    return render_template("map.html", landmarks=landmarks)

# ================== Import Excel ==================
# ================== Import Excel ==================
@app.route('/import_excel', methods=['GET', 'POST'])
def import_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or file.filename == '':
            return render_template("upload_excel.html", error="No file selected.")

        filename = secure_filename(file.filename)
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", filename)
        file.save(file_path)

        try:
            df = pd.read_excel(file_path)
            df = df.dropna(subset=["Place Name"])  # تجاهل الصفوف الفارغة

            for _, row in df.iterrows():
                name = str(row['Place Name']).strip()
                short_name = name.lower().replace(" ", "_")

                coords = str(row['Coordinates']).split(',')
                if len(coords) != 2:
                    continue  # تجاهل أي صف فيه إحداثيات غلط

                lat, lng = coords[0].strip(), coords[1].strip()

                place = Place.query.filter_by(short_name=short_name).first()
                if not place:
                    place = Place(
                        short_name=short_name,
                        name_place=name,
                        place_type=str(row['Type']).strip(),
                        city=str(row['Location']).strip(),
                        lat=lat,
                        lng=lng,
                        link_photo=str(row['Photo URL']).strip(),
                        description=str(row['Description']).strip(),
                        iframe_url=str(row['Iframe URL']).strip(),
                        link_pa=f"place/{short_name}",
                        details_url=f"admin/{short_name}"
                    )
                    db.session.add(place)

            db.session.commit()
            os.remove(file_path)  # تنظيف الملف بعد الاستيراد (اختياري)
            return render_template("upload_excel.html", success="Excel imported successfully!")

        except Exception as e:
            return render_template("upload_excel.html", error=f"Error while processing file: {e}")

    return render_template("upload_excel.html")


# ================== Auth ==================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == '000':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    places = Place.query.all()
    places_list = [(p.link_photo, p.short_name, p.link_pa, p.details_url, p.description) for p in places]
    return render_template("admin_dashboard.html", place=places_list)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ================== CRUD ==================
@app.route('/delete/place/<place_id>', methods=['POST'])
def delete_place(place_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        place = Place.query.filter_by(short_name=place_id).first()
        if not place:
            flash("❌ المكان غير موجود.", "error")
            return redirect(url_for('admin_dashboard'))

        db.session.delete(place)
        db.session.commit()
        flash("✅ تم حذف المكان بنجاح.", "success")
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f"حدث خطأ أثناء الحذف: {str(e)}", "error")
        return redirect(url_for('place_dash'))

@app.route('/add', methods=['GET', 'POST'])
def add_place():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if session.get('logged_in') is True:
            if request.method == 'POST':
                name_place = request.form.get('name_place', '').strip()
                short_name = name_place.lower().replace(" ", "_")
                if Place.query.filter_by(short_name=short_name).first():
                    return render_template("add_place.html", error="❗المكان موجود مسبقًا.", place=request.form)

                iframe_raw = request.form.get('iframe_url', '').strip()
                if "google.com/maps" in iframe_raw:
                    iframe_url = f'<iframe src="{iframe_raw.replace(" ", "")}&output=embed" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy"></iframe>'
                else:
                    iframe_url = iframe_raw

                place = Place(
                    short_name=short_name,
                    name_place=name_place,
                    place_type=request.form.get('place_type', '').strip(),
                    city=request.form.get('city', '').strip(),
                    lat=request.form.get('lat', '').strip(),
                    lng=request.form.get('lng', '').strip(),
                    link_photo=request.form.get('link_photo', '').strip(),
                    description=request.form.get('description', '').strip(),
                    iframe_url=iframe_url,
                    link_pa=f"place/{short_name}",
                    details_url=f"admin/{short_name}"
                )
                db.session.add(place)
                db.session.commit()
                return redirect(url_for('admin_dashboard'))
 
    return render_template("add_place.html")

@app.route('/update-place', methods=['POST'])
def update_place():
    data = request.get_json()
    key = data.get('key')
    place = Place.query.filter_by(short_name=key).first()
    if not place:
        return jsonify({'error': '❌ Place not found'}), 404

    place.name_place = data.get('name_place', '').strip()
    place.description = data.get('description', '').strip()
    place.city = data.get('city', '').strip()
    place.link_photo = data.get('link_photo', '').strip()
    place.iframe_url = data.get('iframe_url', '').strip()
    place.place_type = data.get('place_type', '').strip()
    place.lat = data.get('lat', '').strip()
    place.lng = data.get('lng', '').strip()

    db.session.commit()
    return jsonify({'message': '✅ Place updated successfully'}), 200

# ================== Run ==================
if __name__ == '__main__':
    app.run(port=5001, debug=True)
