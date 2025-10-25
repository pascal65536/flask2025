from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    g,
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy.engine import Engine
from sqlalchemy import func, event
import random
from PIL import Image, ImageDraw, ImageFont
import os
import colorsys
import time
import htmlmin


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///temperature.db"
app.config["SQLALCHEMY_RECORD_QUERIES"] = True

app.config["SECRET_KEY"] = os.urandom(12)

app.config["UPLOAD_FOLDER"] = "static/generated_images"
app.config["FONT_FOLDER"] = "static/fonts"

db = SQLAlchemy(app)

# Создаем папки если их нет
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["FONT_FOLDER"], exist_ok=True)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_name = db.Column(db.String(50), nullable=False)
    measure = db.Column(db.DateTime, nullable=False)
    temperature = db.Column(db.Float, nullable=False)


class GeneratedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    color_hex = db.Column(db.String(7), nullable=False, unique=True)
    filename = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Инициализируем список запросов в контексте запроса
@app.before_request
def before_request():
    g.setdefault('sql_queries', list())


# Обработчик события выполнения SQL
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    import sqlparse
    formatted_sql = sqlparse.format(statement, reindent=True, keyword_case="upper")
    dotg = g.setdefault('sql_queries', list())
    dotg.append({
        'statement': statement,
        'parameters': parameters,
        'start_time': time.time(),
        'formatted_sql': formatted_sql,

    })

def populate_sample_data():
    db.session.query(City).delete()
    cities = [
        ("Moscow", 0, 30),
        ("Saint Petersburg", -20, 20),
        ("Krasnoyarsk", -25, 20),
        ("Novosibirsk", -15, 25),
        ("Sochi", 5, 35),
        ("Yekaterinburg", -10, 25),
        ("Kazan", -5, 28),
        ("Rostov", -2, 32),
    ]
    diff = 3650
    start_date = datetime.now() - timedelta(days=diff)
    for city in cities:
        for day in range(diff):
            date = start_date + timedelta(days=day)
            for measurement in range(12):
                measure_time = date + timedelta(hours=measurement * 2)
                temp = round(random.uniform(city[1], city[2]), 1)
                record = City(city_name=city[0], measure=measure_time, temperature=temp)
                db.session.add(record)
    db.session.commit()


@app.route("/")
def index():
    start_time = time.time()
    recent_images = (
        GeneratedImage.query.order_by(GeneratedImage.created_at.desc()).limit(6).all()
    )
    for recent in recent_images:
        recent.filename = recent.filename.split('.')[0] + '_250.jpg'
    # Рендеринг шаблона
    html_content = render_template(
        "index.html",
        title="Platform",
        name="Добро пожаловать в Experiments Platform",
        experiment="experiment",
        descriptions="Исследуйте возможности веб-разработки, оптимизацию запросов и генерацию изображений",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        recent_images=recent_images,
    )

    # Минификация HTML
    return htmlmin.minify(html_content)


@app.route("/pictures")
@app.route("/pictures/<int:page>")
def pictures(page=1):
    start_time = time.time()
    per_page = 8
    images_pagination = GeneratedImage.query.order_by(
        GeneratedImage.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    for recent in images_pagination:
        recent.filename = recent.filename.split('.')[0] + '_250.jpg'
    # Рендеринг шаблона
    html_content = render_template(
        "pictures.html",
        title="Галерея изображений",
        name="Галерея созданных изображений",
        experiment="experiment",
        descriptions="Все созданные изображения",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        pagination=images_pagination,
        images=images_pagination.items,
    )

    # Минификация HTML
    return htmlmin.minify(html_content)


@app.route("/gena", methods=["GET", "POST"])
def gena():
    start_time = time.time()
    color_hex = request.args.get("color", "#3498db")
    if request.method == "POST":
        color_hex = request.form.get("color", "#3498db")
        check_existing = "check_existing" in request.form
        filename, is_existing = get_or_create_image(color_hex, check_existing)
        if filename:
            msg = f"Изображение создано! Цвет: {color_hex.upper()} {'(из кэша)' if is_existing else '(новое)'}"
            flash(msg, "success")
        else:
            flash("Не удалось создать изображение", "error")
    recent_images = (
        GeneratedImage.query.order_by(GeneratedImage.created_at.desc()).limit(4).all()
    )
    for recent in recent_images:
        recent.filename = recent.filename.split('.')[0] + '_250.jpg'
    # Рендеринг шаблона
    html_content = render_template(
        "gena.html",
        title="Генератор картинок",
        name="Генератор художественных изображений",
        experiment="experiment",
        descriptions="Выберите цвет и создайте уникальное изображение",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        recent_images=recent_images,
        color_hex=color_hex,
    )
    
    # Минификация HTML
    return htmlmin.minify(html_content)

@app.route("/api/clear_images", methods=["POST"])
def clear_images():
    for image in GeneratedImage.query.all():
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    GeneratedImage.query.delete()
    db.session.commit()
    return redirect(url_for("pictures"))


@app.route("/weather1")
def weather1():
    """Оптимизированная версия - один SQL-запрос с GROUP BY"""
    start_time = time.time()
    qs = (
        db.session.query(City.city_name, func.avg(City.temperature).label("avg_temp"))
        .group_by(City.city_name)
        .all()
    )
    results = [{"city": city, "avg_temp": round(avg_temp, 2)} for city, avg_temp in qs]
    results.sort(key=lambda x: x["city"])
    return render_template(
        "query_results.html",
        title="Оптимизированная версия",
        name="Средняя температура по городам",
        experiment="experiment",
        descriptions="Оптимизированная версия - один SQL-запрос с GROUP BY",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        data=results,
    )


@app.route("/weather2")
def weather2():
    """Полуоптимизированная версия - отдельные агрегатные запросы для каждого города"""
    start_time = time.time()
    cities = [city[0] for city in db.session.query(City.city_name).distinct().all()]
    results = []
    for city_name in cities:
        avg_temp = (
            db.session.query(func.avg(City.temperature))
            .filter(City.city_name == city_name)
            .scalar()
        )
        results.append({"city": city_name, "avg_temp": round(avg_temp or 0, 2)})
    results.sort(key=lambda x: x["city"])
    return render_template(
        "query_results.html",
        title="Полуоптимизированная версия",
        name="Средняя температура по городам",
        experiment="experiment",
        descriptions="Полуоптимизированная версия - отдельные агрегатные запросы для каждого города.",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        data=results,
    )


@app.route("/weather3")
def weather3():
    """Неоптимизированная версия - отдельный запрос для каждого города"""
    start_time = time.time()
    cities = [city[0] for city in db.session.query(City.city_name).distinct().all()]
    results = []
    for city_name in cities:
        # Неэффективный запрос - получаем ВСЕ записи и считаем в Python
        qs = db.session.query(City).filter(City.city_name == city_name).all()
        total_temp = sum(city_data.temperature for city_data in qs)
        avg_temp = total_temp / len(qs) if qs else 0
        results.append({"city": city_name, "avg_temp": round(avg_temp, 2)})
    results.sort(key=lambda x: x["city"])
    return render_template(
        "query_results.html",
        title="Неэффективный SQL запрос",
        name="Средняя температура по городам",
        experiment="experiment",
        descriptions="Неэффективный запрос - получаем ВСЕ записи и считаем в Python",
        execution_time=time.time() - start_time, sql_queries=g.get('sql_queries', list()),
        data=results,
    )


def generate_artistic_image(color_hex, size=(1080, 1080)):

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def hsv_to_hex(h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    image = Image.new("RGB", size, color=hex_to_rgb(color_hex))
    draw = ImageDraw.Draw(image)
    width, height = size
    r, g, b = hex_to_rgb(color_hex)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    complementary_h = (h + 0.5) % 1.0
    analogous1_h = (h + 0.08) % 1.0
    analogous2_h = (h - 0.08) % 1.0
    color2 = hsv_to_hex(complementary_h, s, v)
    color3 = hsv_to_hex(analogous1_h, s, min(v + 0.2, 1.0))
    color4 = hsv_to_hex(analogous2_h, s, max(v - 0.2, 0.8))
    cx, cy = width // 2, height // 2
    cr = min(width, height) // 3
    draw.ellipse(
        [cx - cr, cy - cr, cx + cr, cy + cr], fill=color2, outline=color3, width=10
    )
    ss = cr // 2
    draw.rectangle(
        [cx - ss, cy - ss, cx + ss, cy + ss], fill=color4, outline=color2, width=5
    )
    ts = ss // 2
    draw.polygon(
        [cx, cy - ts, cx - ts, cy + ts, cx + ts, cy + ts],
        fill=color3,
        outline=color4,
        width=3,
    )
    font_path = os.path.join(app.config["FONT_FOLDER"], "YandexSansDisplay-Regular.ttf")
    font_size = 100
    font = ImageFont.truetype(font_path, font_size)
    text = f"Color: {color_hex}"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    tw = text_bbox[2] - text_bbox[0]
    draw.text((cx - tw // 2, cy + cr + 30), text, fill=color3, font=font)
    return image


def save_resized_images(filepath, base_filename):
    original_image = Image.open(filepath)
    resized_500 = original_image.resize((500, 500))
    resized_500.save(
        os.path.join(app.config["UPLOAD_FOLDER"], f"{base_filename}_500.webp"), "WEBP"
    )
    resized_250 = original_image.resize((250, 250))
    resized_250.save(
        os.path.join(app.config["UPLOAD_FOLDER"], f"{base_filename}_250.jpg"), "JPEG"
    )


def get_or_create_image(color_hex, check_existing=True):
    color_hex = color_hex.upper()
    if not color_hex.startswith("#"):
        color_hex = "#" + color_hex
    if check_existing:
        existing_image = GeneratedImage.query.filter_by(color_hex=color_hex).first()
        if existing_image:
            return existing_image.filename, True
    filename = f"{color_hex.lstrip('#')}.png"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image = generate_artistic_image(color_hex)
    image.save(filepath, "PNG")
    save_resized_images(filepath, color_hex.lstrip("#"))
    GeneratedImage.query.filter_by(color_hex=color_hex).delete()
    new_image = GeneratedImage(color_hex=color_hex, filename=filename)
    db.session.add(new_image)
    db.session.commit()
    return filename, False


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if db.session.query(City).count() == 0:
            print("Генерация тестовых данных...")
            populate_sample_data()
        else:
            print(f"В базе уже есть {db.session.query(City).count()} записей")

    debug_mode = False
    app.debug = debug_mode
    app.config["DEBUG"] = debug_mode
    app.run(debug=app.debug)
