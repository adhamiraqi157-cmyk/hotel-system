from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, csv, re, chardet, pandas as pd

# ==================== إعداد التطبيق ====================
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'
db = SQLAlchemy(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ==================== MODELS ====================
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    national_id = db.Column(db.String(20), nullable=False)
    passport = db.Column(db.String(50))
    nationality = db.Column(db.String(50))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    check_in = db.Column(db.String(20), nullable=False)
    check_out = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, default=0)
    notes = db.Column(db.String(500), default="")
    customer = db.relationship("Customer")
    room = db.relationship("Room")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # income / expense
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="EGP")
    description = db.Column(db.String(200))

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_name = db.Column(db.String(100))
    check_in = db.Column(db.String(50))
    check_out = db.Column(db.String(50))
    room = db.Column(db.String(100))
    price = db.Column(db.Float)
    currency = db.Column(db.String(10))


# ==================== ROUTES ====================

@app.route("/")
def home():
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        if user == "admin" and pwd == "123":
            return redirect(url_for("dashboard"))
        flash("❌ خطأ في البيانات", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------- ROOMS ----------
@app.route("/rooms")
def rooms_list():
    rooms = Room.query.all()
    return render_template("rooms.html", rooms=rooms)

@app.route("/rooms/add", methods=["GET", "POST"])
def room_add():
    if request.method == "POST":
        new_room = Room(
            number=request.form["number"],
            type=request.form["type"],
            price=request.form["price"],
            status=request.form["status"]
        )
        db.session.add(new_room)
        db.session.commit()
        flash("✅ تم إضافة الغرفة بنجاح", "success")
        return redirect(url_for("rooms_list"))
    return render_template("room_form.html")

@app.route("/rooms/edit/<int:room_id>", methods=["GET", "POST"])
def room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == "POST":
        room.number = request.form["number"]
        room.type = request.form["type"]
        room.price = request.form["price"]
        room.status = request.form["status"]
        db.session.commit()
        flash("✅ تم تعديل بيانات الغرفة", "success")
        return redirect(url_for("rooms_list"))
    return render_template("room_form.html", action="تعديل", room=room)

@app.route("/rooms/delete/<int:room_id>", methods=["POST"])
def room_delete(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash("✅ تم حذف الغرفة بنجاح", "success")
    return redirect(url_for("rooms_list"))


# ---------- FINANCE ----------
@app.route("/finance", methods=["GET", "POST"])
def finance():
    if request.method == "POST":
        t = Transaction(
            date=request.form["date"],
            type=request.form["type"],
            amount=float(request.form["amount"]),
            currency=request.form["currency"],
            description=request.form["description"]
        )
        db.session.add(t)
        db.session.commit()
        flash("✅ تم إضافة العملية المالية بنجاح!", "success")
        return redirect(url_for("finance"))

    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    currencies = [c[0] for c in db.session.query(Transaction.currency).distinct().all()]
    stats = []
    for currency in currencies:
        income = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.type == "income", Transaction.currency == currency
        ).scalar() or 0
        expense = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.type == "expense", Transaction.currency == currency
        ).scalar() or 0
        stats.append({
            "currency": currency,
            "income": income,
            "expense": expense,
            "profit": income - expense
        })
    return render_template("finance.html", transactions=transactions, stats=stats)

@app.route("/finance/delete/<int:id>", methods=["POST"])
def finance_delete(id):
    trans = Transaction.query.get_or_404(id)
    db.session.delete(trans)
    db.session.commit()
    flash("🗑️ تم حذف العملية", "info")
    return redirect(url_for("finance"))

@app.route("/finance/edit/<int:id>", methods=["GET", "POST"])
def finance_edit(id):
    trans = Transaction.query.get_or_404(id)
    if request.method == "POST":
        trans.date = request.form["date"]
        trans.type = request.form["type"]
        trans.amount = float(request.form["amount"])
        trans.currency = request.form["currency"]
        trans.description = request.form["description"]
        db.session.commit()
        flash("✅ تم تعديل العملية بنجاح", "success")
        return redirect(url_for("finance"))
    return render_template("edit_finance.html", trans=trans)


# ---------- IMPORT BOOKINGS ----------
@app.route("/import", methods=["GET", "POST"])
def import_reservations():
    count = 0

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("❌ من فضلك اختر ملف الحجوزات", "danger")
            return redirect(url_for("import_reservations"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        ext = os.path.splitext(filename)[1].lower()

        try:
            # 🧩 قراءة الملف حسب الامتداد
            if ext in [".xls", ".xlsx"]:
                df = pd.read_excel(filepath, engine="openpyxl", dtype=str)
            elif ext == ".csv":
                with open(filepath, "rb") as raw:
                    encoding = chardet.detect(raw.read()).get("encoding", "utf-8")
                df = pd.read_csv(filepath, encoding=encoding, dtype=str)
            else:
                flash("❌ نوع الملف غير مدعوم (استخدم CSV أو Excel فقط)", "danger")
                return redirect(url_for("import_reservations"))

            # تنظيف الأعمدة
            df.columns = [str(c).strip().replace("\\", "/") for c in df.columns]
            headers = list(df.columns)
            flash(f"📋 الأعمدة الموجودة في الملف: {headers}", "info")

            df = df.fillna("").dropna(how="all")
            data = df.to_dict(orient="records")

        except Exception as e:
            flash(f"❌ خطأ أثناء قراءة الملف: {e}", "danger")
            return redirect(url_for("import_reservations"))

        # 🧹 نحذف الحجوزات القديمة
        Reservation.query.delete()
        db.session.commit()

        # 🧾 الأعمدة المحتملة بلغات مختلفة
        name_keys = ["اسم الضيف/الضيوف", "اسم الضيف", "Guest Name"]
        checkin_keys = ["تسجيل الوصول", "Check In"]
        checkout_keys = ["تسجيل المغادرة", "Check Out"]
        room_keys = ["نوع الوحدة", "Room"]
        price_keys = ["السعر", "Your Revenue", "Taxable Revenue"]
        currency_keys = ["العملة", "Currency"]

        # 🔁 نبدأ قراءة البيانات
        for row in data:
            try:
                normalized = {str(k).strip().replace("\\", "/"): str(v).strip() for k, v in row.items()}

                # دالة تساعدنا نجيب أول عمود موجود فعلاً
                def get_value(keys):
                    for k in keys:
                        if k in normalized and normalized[k]:
                            return normalized[k]
                    return ""

                guest = get_value(name_keys) or "غير معروف"
                check_in = get_value(checkin_keys)
                check_out = get_value(checkout_keys)
                room = get_value(room_keys) or "غير محددة"
                price_str = get_value(price_keys) or "0"
                currency = get_value(currency_keys) or "USD"

                # تخطي الصفوف اللي مافيهاش اسم ضيف أو تواريخ
                if guest in ["", "nan", "غير معروف"] and check_in == "":
                    continue

                # تنظيف السعر
                clean = re.sub(r"[^0-9.,]", "", str(price_str))
                try:
                    price = float(clean.replace(",", "")) if clean else 0.0
                except:
                    price = 0.0

                db.session.add(Reservation(
                    guest_name=guest,
                    check_in=check_in,
                    check_out=check_out,
                    room=room,
                    price=price,
                    currency=currency
                ))
                count += 1

            except Exception as e:
                print(f"⚠️ تخطي صف به خطأ: {e}")
                continue

        db.session.commit()
        flash(f"✅ تم استيراد {count} حجز بنجاح من الملف!", "success")
        return redirect(url_for("import_reservations"))

    reservations = Reservation.query.order_by(Reservation.id.desc()).all()
    return render_template("import.html", reservations=reservations)


# ---------- CALENDAR ----------
@app.route("/calendar")
def calendar_view():
    return render_template("calendar.html")

# ---------- TIMELINE ----------
@app.route("/timeline")
def timeline_view():
    return render_template("timeline.html")


# ---------- APIs ----------
@app.route("/api/rooms")
def rooms_api():
    rooms = Room.query.all()
    return jsonify([{"id": r.id, "title": f"غرفة {r.number}"} for r in rooms])

@app.route("/api/bookings")
def bookings_api():
    bookings = Booking.query.all()
    data = [{
        "title": f"غرفة {b.room.number} - {b.customer.name}",
        "start": b.check_in,
        "end": b.check_out
    } for b in bookings]
    return jsonify(data)

@app.route("/api/stats")
def stats():
    return jsonify({
        "total_rooms": Room.query.count(),
        "available": Room.query.filter_by(status="available").count(),
        "booked": Room.query.filter_by(status="booked").count(),
        "maintenance": Room.query.filter_by(status="maintenance").count(),
        "total_bookings": Booking.query.count()
    })


# ---------- INIT ----------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
