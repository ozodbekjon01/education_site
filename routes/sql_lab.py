from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
import sqlite3
import os
import time
import json
import random
import urllib.request

bp = Blueprint('sql_lab', __name__)

SANDBOX_DIR = os.path.join(os.path.dirname(__file__), '..', 'sandboxes')
MAIN_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')
os.makedirs(SANDBOX_DIR, exist_ok=True)

# Default standard database schema and seed data
DEFAULT_SCHEMA_SQL = """
DROP TABLE IF EXISTS baholar;
DROP TABLE IF EXISTS xodimlar;
DROP TABLE IF EXISTS bolimlar;
DROP TABLE IF EXISTS fanlar;
DROP TABLE IF EXISTS talabalar;

-- 1. TALABALAR
CREATE TABLE talabalar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ism TEXT NOT NULL,
    familiya TEXT NOT NULL,
    yosh INTEGER NOT NULL,
    guruh TEXT NOT NULL,
    shahar TEXT NOT NULL,
    stipendiya INTEGER NOT NULL
);

INSERT INTO talabalar (ism, familiya, yosh, guruh, shahar, stipendiya) VALUES
('Anvar', 'Karimov', 20, 'AT-21', 'Toshkent', 1200000),
('Malika', 'Rustamova', 19, 'AT-21', 'Samarqand', 1500000),
('Jasur', 'Aliyev', 21, 'AT-22', 'Buxoro', 900000),
('Dildora', 'Sobirova', 20, 'AT-21', 'Toshkent', 1800000),
('Bobur', 'Qodirov', 22, 'AT-22', 'Farg''ona', 1200000),
('Shahnoza', 'Ismoilova', 19, 'AT-23', 'Andijon', 1500000),
('Sanjar', 'Nazarov', 21, 'AT-23', 'Namangan', 0),
('Zuhra', 'Xolmatova', 20, 'AT-22', 'Toshkent', 1200000),
('Otabek', 'Yuldashev', 22, 'AT-21', 'Xorazm', 1500000),
('Nodira', 'Azimova', 19, 'AT-23', 'Samarqand', 2000000);

-- 2. FANLAR
CREATE TABLE fanlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    oqituvchi TEXT NOT NULL,
    kredit INTEGER NOT NULL,
    soat INTEGER NOT NULL
);

INSERT INTO fanlar (nom, oqituvchi, kredit, soat) VALUES
('Ma''lumotlar Bazasi', 'Dots. Axmedov A.', 6, 60),
('Algoritmlar', 'Prof. Rahimov B.', 6, 60),
('Veb Dasturlash', 'Katta o''qit. Saidov M.', 4, 45),
('Kiberxavfsizlik Asoslari', 'Dots. Umarov K.', 4, 45),
('Sun''iy Intellekt', 'Prof. Zokirov D.', 6, 60);

-- 3. BAHOLAR
CREATE TABLE baholar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talaba_id INTEGER NOT NULL,
    fan_id INTEGER NOT NULL,
    ball INTEGER NOT NULL,
    sana TEXT NOT NULL,
    FOREIGN KEY (talaba_id) REFERENCES talabalar(id),
    FOREIGN KEY (fan_id) REFERENCES fanlar(id)
);

INSERT INTO baholar (talaba_id, fan_id, ball, sana) VALUES
(1, 1, 88, '2026-05-10'),
(1, 2, 92, '2026-05-12'),
(2, 1, 95, '2026-05-10'),
(2, 3, 90, '2026-05-15'),
(3, 1, 74, '2026-05-10'),
(3, 2, 68, '2026-05-12'),
(4, 1, 100, '2026-05-10'),
(4, 4, 85, '2026-05-14'),
(5, 2, 79, '2026-05-12'),
(5, 5, 88, '2026-05-16'),
(6, 3, 91, '2026-05-15'),
(7, 1, 65, '2026-05-10'),
(8, 4, 94, '2026-05-14'),
(9, 5, 82, '2026-05-16'),
(10, 1, 98, '2026-05-10'),
(10, 2, 95, '2026-05-12');

-- 4. BO'LIMLAR
CREATE TABLE bolimlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    xona TEXT NOT NULL
);

INSERT INTO bolimlar (nom, xona) VALUES
('Axborot Texnologiyalari', '304-xona'),
('Dasturiy Muhandislik', '412-xona'),
('Kadrlar Bo''limi', '102-xona'),
('Moliya Bo''limi', '205-xona');

-- 5. XODIMLAR
CREATE TABLE xodimlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ism TEXT NOT NULL,
    lavozim TEXT NOT NULL,
    maosh INTEGER NOT NULL,
    bolim_id INTEGER NOT NULL,
    FOREIGN KEY (bolim_id) REFERENCES bolimlar(id)
);

INSERT INTO xodimlar (ism, lavozim, maosh, bolim_id) VALUES
('Sherzod Alimov', 'Senior Developer', 22000000, 1),
('Guli Karimova', 'Database Administrator', 18000000, 1),
('Farrux Bekov', 'Frontend Developer', 14000000, 2),
('Shahzod Oripov', 'Backend Developer', 16000000, 2),
('Dilnoza Yusupova', 'HR Manager', 9000000, 3),
('Ulug''bek Temirov', 'Bosh Hisobchi', 13000000, 4);
"""

DEFAULT_SAMPLE_QUERIES = [
    {"title": "1. Talabalar ro'yxati (SELECT)", "query": "SELECT * FROM talabalar LIMIT 10;"},
    {"title": "2. Shahar bo'yicha filtrlash (WHERE)", "query": "SELECT * FROM talabalar WHERE shahar = 'Toshkent';"},
    {"title": "3. Guruhlar bo'yicha (GROUP BY & AVG)", "query": "SELECT guruh, COUNT(*) as soni, AVG(stipendiya) as ortacha_stip FROM talabalar GROUP BY guruh;"},
    {"title": "4. Baholarni bog'lash (JOIN)", "query": "SELECT talabalar.ism, fanlar.nom, baholar.ball FROM baholar JOIN talabalar ON baholar.talaba_id = talabalar.id JOIN fanlar ON baholar.fan_id = fanlar.id;"},
    {"title": "5. Xodimlar va Bo'limlar (JOIN & ORDER)", "query": "SELECT xodimlar.ism, xodimlar.maosh, bolimlar.nom FROM xodimlar JOIN bolimlar ON xodimlar.bolim_id = bolimlar.id ORDER BY xodimlar.maosh DESC;"}
]

# Smart fallback dynamic database scenarios
PRESET_AI_SCENARIOS = [
    {
        "domain_name": "E-Commerce Onlayn Do'kon Tizimi",
        "description": "Mahsulotlar, mijozlar, buyurtmalar va toifalarni boshqarish ma'lumotlar bazasi.",
        "schema_sql": """
        DROP TABLE IF EXISTS buyurtma_tarkibi;
        DROP TABLE IF EXISTS buyurtmalar;
        DROP TABLE IF EXISTS mahsulotlar;
        DROP TABLE IF EXISTS toifalar;
        DROP TABLE IF EXISTS mijozlar;

        CREATE TABLE toifalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL
        );
        INSERT INTO toifalar (nom) VALUES ('Smartfonlar'), ('Noutbuklar'), ('Aksessuarlar'), ('Maishiy Texnika');

        CREATE TABLE mahsulotlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            toifa_id INTEGER NOT NULL,
            narx INTEGER NOT NULL,
            ombor_soni INTEGER NOT NULL,
            FOREIGN KEY (toifa_id) REFERENCES toifalar(id)
        );
        INSERT INTO mahsulotlar (nom, toifa_id, narx, ombor_soni) VALUES
        ('iPhone 15 Pro', 1, 14000000, 15),
        ('Samsung Galaxy S24', 1, 12000000, 20),
        ('MacBook Air M3', 2, 16500000, 8),
        ('Lenovo Legion 5', 2, 13000000, 12),
        ('AirPods Pro 2', 3, 3000000, 35),
        ('Samsung Kiryuvgich', 4, 6000000, 5);

        CREATE TABLE mijozlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            shahar TEXT NOT NULL,
            telefon TEXT NOT NULL
        );
        INSERT INTO mijozlar (ism, shahar, telefon) VALUES
        ('Alisher Vohidov', 'Toshkent', '+998901234567'),
        ('Zilola Karimova', 'Samarqand', '+998939876543'),
        ('Javohir Toshov', 'Buxoro', '+998971112233'),
        ('Muxlisa Saidova', 'Farg''ona', '+998994445566');

        CREATE TABLE buyurtmalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mijoz_id INTEGER NOT NULL,
            jami_summa INTEGER NOT NULL,
            sana TEXT NOT NULL,
            holat TEXT NOT NULL,
            FOREIGN KEY (mijoz_id) REFERENCES mijozlar(id)
        );
        INSERT INTO buyurtmalar (mijoz_id, jami_summa, sana, holat) VALUES
        (1, 14000000, '2026-06-01', 'Yetkazildi'),
        (2, 3000000, '2026-06-02', 'Jarayonda'),
        (3, 16500000, '2026-06-03', 'Yetkazildi'),
        (1, 6000000, '2026-06-04', 'Bekor qilindi');
        """,
        "sample_queries": [
            {"title": "1. Barcha mahsulotlar (SELECT)", "query": "SELECT * FROM mahsulotlar;"},
            {"title": "2. Narxi 10 mln dan yuqori tovarlar", "query": "SELECT nom, narx FROM mahsulotlar WHERE narx >= 10000000 ORDER BY narx DESC;"},
            {"title": "3. Toifalar bo'yicha mahsulotlar soni", "query": "SELECT toifalar.nom, COUNT(mahsulotlar.id) as tovar_soni FROM toifalar LEFT JOIN mahsulotlar ON toifalar.id = mahsulotlar.toifa_id GROUP BY toifalar.id;"},
            {"title": "4. Mijozlar va ularning buyurtmalari (JOIN)", "query": "SELECT mijozlar.ism, buyurtmalar.jami_summa, buyurtmalar.holat FROM buyurtmalar JOIN mijozlar ON buyurtmalar.mijoz_id = mijozlar.id;"},
            {"title": "5. O'rtacha mahsulot narxi (AVG)", "query": "SELECT AVG(narx) as ortacha_narx FROM mahsulotlar;"}
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Smartfonlar toifasidagi mahsulotlar",
                "description": "Smartfonlar toifasiga tegishli barcha mahsulotlarning nomi va narxini chiqaring.",
                "hint": "SELECT mahsulotlar.nom, mahsulotlar.narx FROM mahsulotlar JOIN toifalar ON mahsulotlar.toifa_id = toifalar.id WHERE toifalar.nom = 'Smartfonlar';",
                "gold_sql": "SELECT mahsulotlar.nom, mahsulotlar.narx FROM mahsulotlar JOIN toifalar ON mahsulotlar.toifa_id = toifalar.id WHERE toifalar.nom = 'Smartfonlar';"
            },
            {
                "id": 2,
                "title": "Yetkazilgan buyurtmalar",
                "description": "Holati 'Yetkazildi' bo'lgan barcha buyurtmalarning mijoz ismi va summasini chiqaring.",
                "hint": "SELECT mijozlar.ism, buyurtmalar.jami_summa FROM buyurtmalar JOIN mijozlar ON buyurtmalar.mijoz_id = mijozlar.id WHERE buyurtmalar.holat = 'Yetkazildi';",
                "gold_sql": "SELECT mijozlar.ism, buyurtmalar.jami_summa FROM buyurtmalar JOIN mijozlar ON buyurtmalar.mijoz_id = mijozlar.id WHERE buyurtmalar.holat = 'Yetkazildi';"
            }
        ]
    },
    {
        "domain_name": "Shifoxona & Tibbiyot Markazi Tizimi",
        "description": "Shifokorlar, bemorlar, qabullar va diagnozlar ma'lumotlar bazasi.",
        "schema_sql": """
        DROP TABLE IF EXISTS qabullar;
        DROP TABLE IF EXISTS bemorlar;
        DROP TABLE IF EXISTS shifokorlar;
        DROP TABLE IF EXISTS bolimlar;

        CREATE TABLE bolimlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            qavat INTEGER NOT NULL
        );
        INSERT INTO bolimlar (nom, qavat) VALUES ('Kardiologiya', 3), ('Nevrologiya', 2), ('Terapiya', 1), ('Jarrohlik', 4);

        CREATE TABLE shifokorlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            mutaxassislik TEXT NOT NULL,
            tajriba_yil INTEGER NOT NULL,
            bolim_id INTEGER NOT NULL,
            FOREIGN KEY (bolim_id) REFERENCES bolimlar(id)
        );
        INSERT INTO shifokorlar (ism, mutaxassislik, tajriba_yil, bolim_id) VALUES
        ('Dr. Akrom Shodiyev', 'Kardiolog', 12, 1),
        ('Dr. Nilufar Qosimova', 'Nevropatolog', 8, 2),
        ('Dr. Botir Rahmonov', 'Terapevt', 15, 3),
        ('Dr. Sardor Mirzayev', 'Jarroh', 6, 4);

        CREATE TABLE bemorlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            yosh INTEGER NOT NULL,
            qon_guruhi TEXT NOT NULL,
            shahar TEXT NOT NULL
        );
        INSERT INTO bemorlar (ism, yosh, qon_guruhi, shahar) VALUES
        ('Sirojiddin Aliyev', 45, 'A(II)+', 'Toshkent'),
        ('Madina Umarova', 28, 'O(I)+', 'Samarqand'),
        ('Sobir Ergashev', 60, 'B(III)+', 'Andijon'),
        ('Gulbahor Nurmatova', 35, 'AB(IV)+', 'Buxoro');

        CREATE TABLE qabullar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bemor_id INTEGER NOT NULL,
            shifokor_id INTEGER NOT NULL,
            sana TEXT NOT NULL,
            tashxis TEXT NOT NULL,
            tolov INTEGER NOT NULL,
            FOREIGN KEY (bemor_id) REFERENCES bemorlar(id),
            FOREIGN KEY (shifokor_id) REFERENCES shifokorlar(id)
        );
        INSERT INTO qabullar (bemor_id, shifokor_id, sana, tashxis, tolov) VALUES
        (1, 1, '2026-05-10', 'Gipertoniya', 250000),
        (2, 2, '2026-05-11', 'Migren', 200000),
        (3, 3, '2026-05-12', 'Shamollash', 150000),
        (4, 4, '2026-05-14', 'Appenditsit', 800000);
        """,
        "sample_queries": [
            {"title": "1. Shifokorlar ro'yxati (SELECT)", "query": "SELECT * FROM shifokorlar;"},
            {"title": "2. Tajribasi 10 yildan ortiq shifokorlar", "query": "SELECT ism, mutaxassislik, tajriba_yil FROM shifokorlar WHERE tajriba_yil >= 10;"},
            {"title": "3. Bemorlar va ularning tashxisi (JOIN)", "query": "SELECT bemorlar.ism, qabullar.tashxis, qabullar.tolov FROM qabullar JOIN bemorlar ON qabullar.bemor_id = bemorlar.id;"},
            {"title": "4. Shifokorlar bo'yicha jami tushum (SUM)", "query": "SELECT shifokorlar.ism, SUM(qabullar.tolov) as jami_daromad FROM qabullar JOIN shifokorlar ON qabullar.shifokor_id = shifokorlar.id GROUP BY shifokorlar.id;"},
            {"title": "5. O'rtacha bemorlar yoshi (AVG)", "query": "SELECT AVG(yosh) as ortacha_yosh FROM bemorlar;"}
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Kardiologiya bo'limidagi shifokorlar",
                "description": "Kardiologiya bo'limida ishlaydigan shifokorlarning ismi va mutaxassisligini chiqaring.",
                "hint": "SELECT shifokorlar.ism, shifokorlar.mutaxassislik FROM shifokorlar JOIN bolimlar ON shifokorlar.bolim_id = bolimlar.id WHERE bolimlar.nom = 'Kardiologiya';",
                "gold_sql": "SELECT shifokorlar.ism, shifokorlar.mutaxassislik FROM shifokorlar JOIN bolimlar ON shifokorlar.bolim_id = bolimlar.id WHERE bolimlar.nom = 'Kardiologiya';"
            }
        ]
    },
    {
        "domain_name": "Avtomobillar Ijarasi (Car Rental) Tizimi",
        "description": "Mashinalar, mijozlar, ijaralar va to'lovlar ma'lumotlar bazasi.",
        "schema_sql": """
        DROP TABLE IF EXISTS ijaralar;
        DROP TABLE IF EXISTS avtomobillar;
        DROP TABLE IF EXISTS brendlar;
        DROP TABLE IF EXISTS mijozlar;

        CREATE TABLE brendlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            mamlakat TEXT NOT NULL
        );
        INSERT INTO brendlar (nom, mamlakat) VALUES ('Chevrolet', 'AQSh/O''zbekiston'), ('BMW', 'Germaniya'), ('BYD', 'Xitoy'), ('Toyota', 'Yaponiya');

        CREATE TABLE avtomobillar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            brend_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            kunlik_narx INTEGER NOT NULL,
            holat TEXT NOT NULL,
            FOREIGN KEY (brend_id) REFERENCES brendlar(id)
        );
        INSERT INTO avtomobillar (model, brend_id, yil, kunlik_narx, holat) VALUES
        ('Malibu 2', 1, 2024, 700000, 'Mavjud'),
        ('Tracker 2', 1, 2023, 500000, 'Ijarada'),
        ('BMW X5', 2, 2024, 1800000, 'Mavjud'),
        ('BYD Song Plus', 3, 2024, 650000, 'Ijarada'),
        ('Toyota Camry 70', 4, 2022, 800000, 'Mavjud');

        CREATE TABLE mijozlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            prava_raqam TEXT NOT NULL,
            telefon TEXT NOT NULL
        );
        INSERT INTO mijozlar (ism, prava_raqam, telefon) VALUES
        ('Jamshid Ergashev', 'AA1234567', '+998901112233'),
        ('Bekzod Saidov', 'AB7654321', '+998933334455'),
        ('Sarvar Qodirov', 'AC9988776', '+998977778899');

        CREATE TABLE ijaralar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            avto_id INTEGER NOT NULL,
            mijoz_id INTEGER NOT NULL,
            kun_soni INTEGER NOT NULL,
            jami_narx INTEGER NOT NULL,
            sana TEXT NOT NULL,
            FOREIGN KEY (avto_id) REFERENCES avtomobillar(id),
            FOREIGN KEY (mijoz_id) REFERENCES mijozlar(id)
        );
        INSERT INTO ijaralar (avto_id, mijoz_id, kun_soni, jami_narx, sana) VALUES
        (2, 1, 3, 1500000, '2026-06-01'),
        (4, 2, 5, 3250000, '2026-06-02'),
        (1, 3, 2, 1400000, '2026-06-03');
        """,
        "sample_queries": [
            {"title": "1. Mavjud avtomobillar (SELECT)", "query": "SELECT * FROM avtomobillar WHERE holat = 'Mavjud';"},
            {"title": "2. Kunlik narxi 700 mingdan arzon mashinalar", "query": "SELECT model, kunlik_narx FROM avtomobillar WHERE kunlik_narx <= 700000;"},
            {"title": "3. Mashinalar va ularning brendlari (JOIN)", "query": "SELECT avtomobillar.model, brendlar.nom as brend, avtomobillar.kunlik_narx FROM avtomobillar JOIN brendlar ON avtomobillar.brend_id = brendlar.id;"},
            {"title": "4. Mijozlar ijaraga olgan mashinalar", "query": "SELECT mijozlar.ism, avtomobillar.model, ijaralar.kun_soni, ijaralar.jami_narx FROM ijaralar JOIN mijozlar ON ijaralar.mijoz_id = mijozlar.id JOIN avtomobillar ON ijaralar.avto_id = avtomobillar.id;"},
            {"title": "5. Jami tushum summasi (SUM)", "query": "SELECT SUM(jami_narx) as jami_daromad FROM ijaralar;"}
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Mavjud BMW mashinalari",
                "description": "Brendi BMW bo'lgan va holati 'Mavjud' bo'lgan avtomobillarning modeli va narxini chiqaring.",
                "hint": "SELECT avtomobillar.model, avtomobillar.kunlik_narx FROM avtomobillar JOIN brendlar ON avtomobillar.brend_id = brendlar.id WHERE brendlar.nom = 'BMW' AND avtomobillar.holat = 'Mavjud';",
                "gold_sql": "SELECT avtomobillar.model, avtomobillar.kunlik_narx FROM avtomobillar JOIN brendlar ON avtomobillar.brend_id = brendlar.id WHERE brendlar.nom = 'BMW' AND avtomobillar.holat = 'Mavjud';"
            }
        ]
    }
]

def get_user_db_path():
    user_id = session.get('user_id', 'guest')
    return os.path.join(SANDBOX_DIR, f'user_{user_id}.db')

def init_sandbox_db(db_path, schema_sql=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("PRAGMA foreign_keys = OFF;")
        # Clean out any old tables from previous scenarios
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        existing = [r[0] for r in c.fetchall()]
        for tbl in existing:
            try:
                c.execute(f"DROP TABLE IF EXISTS {tbl}")
            except Exception:
                pass
        conn.commit()

        sql_to_run = schema_sql if schema_sql else DEFAULT_SCHEMA_SQL
        try:
            conn.executescript(sql_to_run)
        except Exception as e:
            # Resilient statement-by-statement execution
            statements = [s.strip() for s in sql_to_run.split(';') if s.strip()]
            for stmt in statements:
                try:
                    c.execute(stmt)
                except Exception as st_err:
                    pass
        c.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
    finally:
        conn.close()

def get_db_connection():
    db_path = get_user_db_path()
    if not os.path.exists(db_path):
        init_sandbox_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
def get_active_ai_keys():
    """Fetch active AI API keys from main database"""
    if not os.path.exists(MAIN_DB_PATH):
        return []
    try:
        conn = sqlite3.connect(MAIN_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM ai_api_keys WHERE is_active=1 ORDER BY id DESC")
        keys = c.fetchall()
        conn.close()
        return keys
    except Exception:
        return []

def get_schema_dict():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row['name'] for row in c.fetchall()]
    schema = {}
    for tbl in tables:
        c.execute(f"PRAGMA table_info({tbl})")
        schema[tbl] = [{"name": r['name'], "type": r['type']} for r in c.fetchall()]
    conn.close()
    return schema

def get_schema_and_sample_rows():
    """Introspect current sandbox database: tables, columns and real sample rows"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row['name'] for row in c.fetchall()]
    details = []
    for tbl in tables:
        c.execute(f"PRAGMA table_info({tbl})")
        cols = [f"{r['name']} ({r['type']})" for r in c.fetchall()]
        
        try:
            c.execute(f"SELECT * FROM {tbl} LIMIT 3")
            sample_rows = [list(r) for r in c.fetchall()]
        except Exception:
            sample_rows = []
            
        details.append(f"- Jadval '{tbl}': Ustunlar: [{', '.join(cols)}] | Namuna qatorlar: {sample_rows}")
    conn.close()
    return "\n".join(details)

def generate_algorithmic_dynamic_task():
    """Smart algorithmic challenge generator that creates rich, varied SQL challenges from live schema without fixed templates"""
    schema = get_schema_dict()
    if not schema:
        return {
            "source": "Dinamik Generator",
            "title": "Baza bilan tanishish",
            "difficulty": "Oson",
            "description": "Ma'lumotlar bazasidagi dastlabki ma'lumotlarni ko'rish uchun so'rov yozing.",
            "hint": "SELECT * FROM talabalar LIMIT 10;",
            "gold_sql": "SELECT * FROM talabalar LIMIT 10;"
        }

    tables = list(schema.keys())
    conn = get_db_connection()
    c = conn.cursor()

    # Find foreign key relationships for intelligent JOIN challenges
    foreign_keys = []
    for tbl in tables:
        try:
            fk_list = c.execute(f"PRAGMA foreign_key_list({tbl})").fetchall()
            for fk in fk_list:
                ref_tbl = fk[2]
                from_col = fk[3]
                to_col = fk[4]
                if ref_tbl in tables:
                    foreign_keys.append((tbl, from_col, ref_tbl, to_col))
        except Exception:
            pass

    # Pick random table
    tbl = random.choice(tables)
    cols_info = schema[tbl]
    col_names = [col["name"] for col in cols_info]
    num_cols = [col["name"] for col in cols_info if any(t in col["type"].upper() for t in ["INT", "REAL", "NUM", "FLOAT", "DEC"])]
    text_cols = [col["name"] for col in cols_info if any(t in col["type"].upper() for t in ["TEXT", "CHAR", "VARCHAR", "STRING"])]

    # Fetch sample rows
    try:
        c.execute(f"SELECT * FROM {tbl} LIMIT 10")
        sample_rows = [list(r) for r in c.fetchall()]
    except Exception:
        sample_rows = []
    conn.close()

    generators = []

    # 1. JOIN Challenge (if FK exists)
    if foreign_keys:
        t1, c1, t2, c2 = random.choice(foreign_keys)
        cols_t1 = [col["name"] for col in schema.get(t1, []) if col["name"] != c1]
        cols_t2 = [col["name"] for col in schema.get(t2, []) if col["name"] != c2]
        sel_c1 = cols_t1[0] if cols_t1 else f"{t1}.id"
        sel_c2 = cols_t2[0] if cols_t2 else f"{t2}.id"
        generators.append({
            "source": "Dinamik Tahlilchi",
            "title": f"'{t1.capitalize()}' va '{t2.capitalize()}' jadvallarini bog'lash (JOIN)",
            "difficulty": "O'rta",
            "description": f"'{t1}' va '{t2}' jadvallarini INNER JOIN orqali bog'lab, '{t1}.{sel_c1}' hamda '{t2}.{sel_c2}' ustunlarini chiqaring.",
            "hint": f"SELECT {t1}.{sel_c1}, {t2}.{sel_c2} FROM {t1} JOIN {t2} ON {t1}.{c1} = {t2}.{c2};",
            "gold_sql": f"SELECT {t1}.{sel_c1}, {t2}.{sel_c2} FROM {t1} JOIN {t2} ON {t1}.{c1} = {t2}.{c2};"
        })

    # 2. GROUP BY & Aggregation
    if text_cols and num_cols:
        g_col = random.choice(text_cols)
        n_col = random.choice(num_cols)
        agg_func = random.choice(["AVG", "SUM", "MAX", "COUNT"])
        generators.append({
            "source": "Dinamik Tahlilchi",
            "title": f"'{g_col}' bo'yicha guruhlash va {agg_func}() hisoblash",
            "difficulty": "O'rta",
            "description": f"'{tbl}' jadvalida '{g_col}' bo'yicha guruhlab, har bir guruh uchun '{n_col}' ustunining {agg_func} qiymatini 'natija' nomi bilan hisoblang.",
            "hint": f"SELECT {g_col}, {agg_func}({n_col}) as natija FROM {tbl} GROUP BY {g_col};",
            "gold_sql": f"SELECT {g_col}, {agg_func}({n_col}) as natija FROM {tbl} GROUP BY {g_col};"
        })

    # 3. Numeric Filter with comparison
    if num_cols and sample_rows:
        n_col = random.choice(num_cols)
        col_idx = col_names.index(n_col)
        vals = [r[col_idx] for r in sample_rows if isinstance(r[col_idx], (int, float))]
        if vals:
            mid_val = sorted(vals)[len(vals) // 2]
            op = random.choice([">=", "<=", ">"])
            generators.append({
                "source": "Dinamik Tahlilchi",
                "title": f"'{n_col}' ustunini {op} {mid_val} sharti bilan filtrlash",
                "difficulty": "Oson",
                "description": f"'{tbl}' jadvalidan '{n_col}' qiymati {mid_val} dan {('katta yoki teng' if op == '>=' else 'kichik yoki teng' if op == '<=' else 'katta')} bo'lgan barcha qatorlarni tanlang.",
                "hint": f"SELECT * FROM {tbl} WHERE {n_col} {op} {mid_val};",
                "gold_sql": f"SELECT * FROM {tbl} WHERE {n_col} {op} {mid_val};"
            })

    # 4. Text Search / Filter
    if text_cols and sample_rows:
        t_col = random.choice(text_cols)
        t_idx = col_names.index(t_col)
        t_vals = [str(r[t_idx]) for r in sample_rows if r[t_idx] is not None]
        if t_vals:
            chosen_val = random.choice(t_vals)
            generators.append({
                "source": "Dinamik Tahlilchi",
                "title": f"'{t_col}' bo'yicha qidiruv (WHERE)",
                "difficulty": "Oson",
                "description": f"'{tbl}' jadvalidan '{t_col}' ustunida '{chosen_val}' qiymatiga ega bo'lgan qatorlarni ajratib oling.",
                "hint": f"SELECT * FROM {tbl} WHERE {t_col} = '{chosen_val}';",
                "gold_sql": f"SELECT * FROM {tbl} WHERE {t_col} = '{chosen_val}';"
            })

    # 5. Order by and Limit
    if col_names:
        o_col = random.choice(num_cols or col_names)
        generators.append({
            "source": "Dinamik Tahlilchi",
            "title": f"'{o_col}' bo'yicha top-5 ma'lumotlarni saralash",
            "difficulty": "Oson",
            "description": f"'{tbl}' jadvalidagi eng yuqori (kamayish tartibidagi) dastlabki 5 ta yozuvni '{o_col}' bo'yicha tartiblab chiqaring.",
            "hint": f"SELECT * FROM {tbl} ORDER BY {o_col} DESC LIMIT 5;",
            "gold_sql": f"SELECT * FROM {tbl} ORDER BY {o_col} DESC LIMIT 5;"
        })

    if generators:
        return random.choice(generators)

    return {
        "source": "Dinamik Tahlilchi",
        "title": f"'{tbl.capitalize()}' jadvali tahlili",
        "difficulty": "Oson",
        "description": f"'{tbl}' jadvalidagi dastlabki 10 ta qatorni chiqaring.",
        "hint": f"SELECT * FROM {tbl} LIMIT 10;",
        "gold_sql": f"SELECT * FROM {tbl} LIMIT 10;"
    }

FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "groq/compound-mini"
]

def robust_extract_json(text: str):
    """Reliably extracts and parses JSON object from AI output stripping thinking/markdown fences"""
    import re
    text = text.strip()
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<thought>[\s\S]*?</thought>', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE).strip()

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            candidate = re.sub(r',\s*([\]\}])', r'\1', candidate)
            return json.loads(candidate, strict=False)
    raise ValueError("JSON obyekt topilmadi")

def call_groq_ai_json(api_key: str, initial_model: str, system_prompt: str, user_prompt: str, max_tokens: int = 3500):
    """Execute Groq AI request with multi-model automatic failover"""
    models = [initial_model] + [m for m in FALLBACK_MODELS if m != initial_model]
    url = "https://api.groq.com/openai/v1/chat/completions"

    for m in models:
        if not m:
            continue
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        payload = json.dumps({
            "model": m,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 1.0,
            "max_tokens": max_tokens
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content_str = res_data["choices"][0]["message"]["content"].strip()
                parsed = robust_extract_json(content_str)
                return parsed, m
        except Exception as e:
            print(f"[GROQ AI CALL FAILED with model {m}]: {e}")
            continue

    return None, None

RANDOM_DOMAINS = [
    "Avtomobil ehtiyot qismlari do'koni", "Mobil aloqa operatorlari", "Teleskoplar va kuzatuvlar",
    "Avtomobil turar joylari (Parking)", "FHDYo va nikoh qaydlari", "Maktab va o'quvchilar",
    "Avtobuslar parki (Avtosaroy)", "Psixiatriya va ruhiy sog'lomlashtirish", "Tasviriy san'at galereyasi",
    "Politsiya va jinoyat qidiruv", "Kompaniya serverlari va bulutli xizmatlar", "Elektr transport vositalari ishlab chiqarish",
    "Bionik protezlar markazi", "Jahon urushlari xronologiyasi", "Ovoz yozish studiyasi",
    "O'zga sayyoraliklar kemalari (UFO)", "Golf klublari", "Kanalizatsiya tizimlari",
    "Osmono'par binolar (Skyscrapers)", "Boks va jang san'atlari", "Hayvonlar kasalxonasi (Veterinariya)",
    "Interyer dizayni studiyasi", "Eski binolarni buzish va tozalash", "Kosmik sayyohlik agentligi",
    "Qonun chiqaruvchi palata (Parlament)", "Oltin va mis konlari", "Elektron auksion tizimi",
    "Tez tibbiy yordam stansiyasi", "O'yinchoqlar fabrikasi", "Katta qurilish texnikalari",
    "Sayyohlik kruiz kemalari", "Kosmik teleskoplar", "Tergov qo'mitasi",
    "Virtual reallik (VR) platformasi", "Vaqt mashinasi tajribalari", "Tarixiy shaxslar va imperatorlar",
    "Qushlar migratsiyasi", "Bionik implantlar va protezlar", "Notarius va hujjatlar",
    "Bolalar bog'chasi va tarbiyachilar", "Qayta ishlash zavodlari (Recycling)", "Mehmonxonalar tarmog'i (Hotel)",
    "Koinotlararo portal nazoratchilari", "Futbol chempionati va klublar", "Avtomobillarga texnik xizmat ko'rsatish (Avtoservis)",
    "Kosmetika va parfyumeriya tarmog'i", "Shaffof shisha va oyna fabrikasi", "Zargarlik buyumlari do'koni",
    "Olimpiada qatnashchilari bazasi", "Tog' chang'i kurorti", "O'qituvchilar malakasini oshirish",
    "Iste'dodlar shousi", "O'yin yaratish (Gamedev) studiyasi", "Suv parki va o'yin kulgilar (Aquapark)",
    "Konserva fabrikasi", "Jonli ijro (Live concert) maskanlari", "IT kompaniya va dasturlash jamoalari",
    "Immigratsiya va vizalar", "Qadimiy tillar va yozuvlar", "Muzliklarni tadqiq etish",
    "Pensiya va ijtimoiy ta'minot", "Meteoritlar va asteroidlar katalogi", "Dinlar va mifologiyalar bazasi",
    "Top-fitness klublar tarmog'i", "Alpinizm va tog' cho'qqilari", "Gid va sayyohlar (Turizm)",
    "Pazandachilik maktabi", "Katta yuk avtomobillari parki", "Organik mahsulotlar fermasi",
    "Yulduzlar va galaktikalar arxivi", "Optika va ko'zoynaklar do'koni", "Katta hajmdagi hayvonot bog'i (Zoo)",
    "Laboratoriya va tibbiy tahlillar", "Tennis turnirlari", "Antikvar buyumlar auksioni",
    "Iqlim o'zgarishi monitoringi", "Buyumlar interneti (IoT) tarmog'i", "Blokcheyn tarmog'i",
    "Nobel mukofoti sovrindorlari", "Ekstremal sport turlari markazi", "Konveyer yuk tashish",
    "Robotlar va avtomatlashtirish", "Mevali bog'lar", "Tirbandlikni monitoring qilish tizimi",
    "Startap inkubatorlari", "G'alla va bug'doy omborlari", "Sun'iy intellekt tadqiqotlari markazi",
    "Qo'g'irchoq teatri", "Farmatsevtika zavodi", "Kiyim-kechak brendlari va fabrikalar",
    "Aeroport va parvozlar", "Fazoni tadqiq etish agentligi", "Kutubxona va kitoblar do'koni",
    "Pochta va kuryerlik xizmati", "Yong'in xavfsizligi stansiyalari", "Parrandachilik fabrikasi",
    "Nonvoyxonalar tarmog'i", "Dengiz florasi va faunasi", "Tog' jinslari va minerallar qazib olish",
    "Kosmik yuk tashish xizmati", "Qurilish kompaniyasi va loyihalar", "Dorixonalar tarmog'i",
    "Yovvoyi tabiatni qutqarish markazi", "Chorvachilik va mollar", "Dronlar va ularni boshqarish",
    "Olimpiya o'yinlari qatnashchilari", "Tez yurar poezdlar tarmog'i", "Ko'z kasalliklari klinikasi",
    "Metropoliten va bekatlar", "Ijtimoiy tarmoq foydalanuvchilari", "Talabalar yotoqxonasi (Kampus)",
    "Velosport marafonlari", "Shirinliklar va tortlar pishiriqxonalari", "Davlat xizmatlari markazi (DXM)",
    "Uy-joy shirkatlari (TShJ)", "Smart Smartfonlar ishlab chiqarish", "Ko'chmas mulk agentligi (Rieltorlar)",
    "Choy plantatsiyalari", "Modalar namoyishi va dizaynerlar", "Kamping va tabiat qo'ynida dam olish",
    "Poyezdlar va temir yo'l stansiyalari", "Dengiz porti va yuk kemalari", "Xalqaro elchixonalar tarmog'i",
    "Oliy o'quv yurti va professorlar", "O'simliklar urug'lari banki", "Korrupsiyaga qarshi kurashish agentligi",
    "Ochiq kinoteatrlar", "Maratonga tayyorgarlik markazi", "Qadimgi xaritalar kolleksiyasi",
    "Botanika bog'i", "3D bosmaxona va modellashtirish", "Bakteriologik laboratoriya",
    "Qamoqxona va mahbuslar arxivi", "Pishloq zavodi", "Logistika va yuk tashish (Kargo)",
    "Passport stoli va fuqarolar", "Sanatoriya va dam olish maskanlari", "Gullar yetkazib berish xizmati",
    "Biometrik ma'lumotlar bazasi", "Bemorlarni parvarishlash markazi", "Mehmonxonalar va kvartiralar ijarasi",
    "Sirli orollar katalogi", "Sport tovarlari markazi", "Qizil kitobga kiritilgan hayvonlar",
    "Hasharotlar va entomologiya", "Mudofaa vazirligi va harbiy qismlar", "Kafelar va qahvaxonalar",
    "Poyezd chiptalari sotuvi", "O'rmon xo'jaligi", "Katta savdo markazi (Mall)",
    "Samuraylar va klanlar", "Bozor va rastalar (Marketplace)", "Supermarketlar tarmog'i",
    "Taksi xizmati (Yandex/Uber)", "Poyabzal fabrikasi", "Avtopoyga (Formula-1)",
    "Vaksina ishlab chiqarish", "Shajalar va ajdodlar arxivi", "Yo'qolgan shaharlar",
    "Genetika tadqiqotlari markazi", "Ovozli kitoblar (Audiobooks) platformasi", "Halol oziq-ovqat sertifikatlari",
    "Astronomik observatoriya", "Vulqonlar va otilishlar", "Galaktikalararo savdo federatsiyasi",
    "Texnik qo'llab-quvvatlash markazi (Call Center)", "Xosting provayderi xizmatlari", "Kosmik sun'iy yo'ldoshlar tarmog'i",
    "Ziravorlar bozori", "Badiiy ko'rgazmalar", "Jodu va afsunlar akademiyasi",
    "O'zga sayyoraliklar signallari monitoringi", "Kosmik kemalar va uchirish stansiyalari", "Kiberxavfsizlik va xakerlik xurujlari",
    "Qurilish mollari bozori", "Telekommunikatsiya va internet provayderi", "Qora tuynuklar tadqiqoti",
    "Musiqiy festival va konsertlar", "Sport ligasi (Basketbol, Voleybol)", "Velo-do'konlar tarmog'i",
    "Eksport va Import kompaniyasi", "Tarixiy obidalar restavratsiyasi", "Qon topshirish markazi",
    "Oziq-ovqat yetkazib berish (Delivery)", "Kimyo laboratoriyasi", "Qadimiy sivilizatsiyalar arxivi",
    "Onkologiya markazi", "Koinot missiyalari va kosmonavtlar", "Kardiologiya va yurak jarrohligi",
    "Akademik nashrlar va maqolalar", "Katta ko'p tarmoqli shifoxona", "Qadimgi tangalar va numizmatika",
    "Fermerlik va qishloq xo'jaligi", "Sirlarni saqlash agentligi", "Quyosh va shamol elektr stansiyalari",
    "Radio stansiyasi va eshittirishlar", "O'quv markazlari va kurslar", "Kvant kompyuterlari laboratoriyasi",
    "Gul do'konlari tarmog'i", "Internet buyumlar (IoT) sensorlari", "Xazina qidiruvchilar assotsiatsiyasi",
    "Kriptovalyuta birjasi", "Restoranlar tarmog'i", "Uy jihozlari va mebel do'koni",
    "Fotografiya studiyasi", "Uzumzorlar va vinochilik", "Eko-uylar va yashil qishloqlar",
    "Superqahramonlar reestri", "Telekanal va dasturlar", "Bojxona xizmati",
    "Shaxmat chempionati", "Teatr va sahna asarlari", "Katta kinoteatrlar tarmog'i",
    "Soliq idorasi va to'lovlar", "Onlayn ta'lim platformasi (E-learning)", "Elektronika do'koni tarmog'i",
    "Suv resurslarini boshqarish", "Baliqchilik va dengiz mahsulotlari", "Epidemiologiya nazorati",
    "Sud va jinoyat ishlari", "Ulgurji savdo bazasi", "Grantlar va stipendiyalar",
    "Ot sporti va ippodrom", "Arxeologik qazishmalar", "Stadion va o'rindiqlar",
    "Qurolli kuchlar texnikalari", "Tish shifoxonasi (Stomatologiya)", "Milliy bog'lar va qo'riqxonalar",
    "Data Markazlari (Data Center)", "Ravers va elektron musiqa klublari", "Madaniyat saroylari",
    "Sirk va ko'ngilochar tomoshalar", "Plastik jarrohlik markazi", "Anime va komikslar do'koni",
    "Oy stansiyasi xodimlari", "Sayyoralararo transport tizimi", "Suzish havzalari va suv sporti",
    "Shahar meri va munitsipalitet", "Robototexnika to'garagi", "Tarixiy muzey va artefaktlar",
    "Fizika tadqiqotlari (Kollayderlar)", "Mars koloniyasi va yashash modullari", "Yo'l patrul xizmati (GAI)",
    "Markaziy kutubxona arxivi", "Issiqxonalar (Teplitsalar)", "Suv quvurlari va santexnika",
    "Xalqaro Kosmik Stansiya (XKS)", "Sinfdan tashqari to'garaklar", "Bolalar lagerlari va dam olish maskanlari",
    "Onlayn do'kon (E-commerce)", "Qishloq xo'jaligi texnikalari", "Kino ishlab chiqarish studiyasi",
    "Ko'priklar va yo'l qurilishi", "Chakana savdo kirmish-chiqimlari", "Bojxona nazorati va deklaratsiyalar",
    "Qahva plantatsiyalari", "Ekologik ofatlar xronologiyasi", "Sehrgarlar va afsonaviy mavjudotlar",
    "Aviakompaniya chiptalari va reyslar", "Aqlli uylar (Smart Home) tizimlari", "Zilzilalar va seysmologiya stansiyalari",
    "Saylovlar va ovoz berish tizimi", "Kiber-sport (Esports) jamoalari", "Talabalar almashinuv dasturi",
    "Mobil ilovalar do'koni", "Ilmiy tadqiqot instituti", "Zaharli o'simliklar",
    "Kosmetologiya va dermatologiya", "Avtosalon va avtomobillar ijarasi (Rent a Car)",
]

def generate_ai_database_scenario(domain_name=None):
    """Generate a complete new Database scenario completely autonomously by forcing a random topic"""
    keys = get_active_ai_keys()
    if not keys:
        chosen = random.choice(PRESET_AI_SCENARIOS)
        return chosen

    key_row = random.choice(keys)
    api_key = key_row["api_key"]
    model_name = key_row["model_name"] or "openai/gpt-oss-120b"

    import uuid
    random_seed = uuid.uuid4().hex[:8]
    
    # Force a unique topic every time unless explicitly provided!
    forced_topic = domain_name if domain_name else random.choice(RANDOM_DOMAINS)

    system_prompt = (
        "Siz professional Ma'lumotlar Bazasi arxitektori va ijodkor SQL o'qituvchisisiz. "
        "Vazifangiz: Talabalarning bilimini oshirish uchun MUTLAQO YANGI, MUSTAQIL, REALISTIK va KREATIV SQLite ma'lumotlar bazasi ssenariysini noldan yaratish. "
        f"DIQQAT! SIZNING BUGUNGI MAVZUYINGIZ: **{forced_topic.upper()}**. Faqatgina mana shu soha bo'yicha jadvallar tuzing!\n"
        "QAT'IY QOIDALAR:\n"
        f"1. Soha/mavzu sifatida albatta '{forced_topic}' ni tanlang va unga tegishli kamida 3-4 ta o'zaro FOREIGN KEY orqali bog'langan jadvallar tuzing.\n"
        "2. Har bir jadvalga kamida 4-6 tadan realistik, qiziqarli ma'lumotlar kiritilsin (INSERT INTO ...).\n"
        "3. 'sample_queries' ro'yxatida ushbu baza bo'yicha 5 ta namuna so'rov bering (SELECT, WHERE, JOIN, GROUP BY, ORDER BY).\n"
        "4. 'tasks' ro'yxatida talabalar bajarishi uchun 3-4 ta turli darajadagi (Oson, O'rta, Murakkab) topshiriq va ularning xatosiz 'gold_sql' SELECT kodini yozing.\n"
        "5. Javobni FAQAT toza JSON formatida quyidagi aniq strukturada qaytaring:\n"
        "{\n"
        f'  "domain_name": "{forced_topic} tizimi (O\'zbek tilida)",\n'
        '  "description": "Baza haqida 1-2 gaplik qisqa tavsif",\n'
        '  "schema_sql": "DROP TABLE IF EXISTS ...; CREATE TABLE ...; INSERT INTO ...;",\n'
        '  "sample_queries": [\n'
        '    {"title": "1. Oddiy tanlash (SELECT)", "query": "SELECT ...;"},\n'
        '    {"title": "2. Shartli filtrlash (WHERE)", "query": "SELECT ... WHERE ...;"},\n'
        '    {"title": "3. Jadvallarni bog\'lash (JOIN)", "query": "SELECT ... JOIN ...;"},\n'
        '    {"title": "4. Guruhlash va hisoblash (GROUP BY)", "query": "SELECT ... GROUP BY ...;"},\n'
        '    {"title": "5. Tartiblash va cheklash (ORDER BY)", "query": "SELECT ... ORDER BY ...;"}\n'
        '  ],\n'
        '  "tasks": [\n'
        '    {\n'
        '      "id": 1,\n'
        '      "title": "Topshiriq sarlavhasi",\n'
        '      "difficulty": "Oson",\n'
        '      "description": "Vazifa matni (O\'zbek tilida)",\n'
        '      "hint": "Maslahat",\n'
        '      "gold_sql": "SELECT ..."\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Esda tuting: Markdown (```json) belgilari qo'shmang, to'g'ridan to'g'ri { bilan boshlang va } bilan tugating."
    )

    user_prompt = (
        f"Iltimos, yuqoridagi qoidalarga to'liq amal qilib, '{forced_topic}' sohasida to'liq ma'lumotlar bazasini yarating. [Seed: {random_seed}]"
    )

    parsed_json, used_model = call_groq_ai_json(api_key, model_name, system_prompt, user_prompt, max_tokens=3800)
    if parsed_json and "schema_sql" in parsed_json:
        parsed_json["source"] = f"Groq AI ({used_model})"
        return parsed_json

    chosen = random.choice(PRESET_AI_SCENARIOS)
    chosen["source"] = "smart_preset_fallback"
    return chosen

def generate_groq_ai_task():
    """Generate dynamic, 100% unique SQL challenge based on active DB tables and sample data"""
    keys = get_active_ai_keys()
    db_context = get_schema_and_sample_rows()
    
    if not keys or not db_context:
        return generate_algorithmic_dynamic_task()

    key_row = random.choice(keys)
    api_key = key_row["api_key"]
    model_name = key_row["model_name"] or "openai/gpt-oss-120b"

    import uuid
    task_seed = uuid.uuid4().hex[:8]

    system_prompt = (
        "Siz professional Ma'lumotlar Bazasi arxitektori va ijodkor SQL instruktorisiz. "
        "Sizga foydalanuvchining ayni paytda faol SQLite ma'lumotlar bazasi jadvallari, ustunlari va real namuna ma'lumotlari beriladi. "
        "Vazifangiz: Berilgan ma'lumotlar asosida talaba uchun MUTLAQO YANGI, O'ZIGA XOS, QIZIQARLI va REALISTIK SQL topshirig'i (challenge) yaratish. "
        "QAT'IY QOIDALAR:\n"
        "1. Hech qanday shablon yoki takroriy namunalardan foydalanmang. Baza ustunlarini tahlil qilib, o'zingiz yangi mantiqiy topshiriq o'ylab toping.\n"
        "2. 'gold_sql' maydonida ushbu topshiriqni 100% to'g'ri bajaruvchi aniq, xatosiz ishlaydigan SQLite SELECT so'rovini yozing.\n"
        "3. 'hint' maydonida talabaga yo'llanma bering.\n"
        "4. Javobni FAQAT toza JSON formatida quyidagi strukturada qaytaring:\n"
        "{\n"
        '  "title": "Topshiriq sarlavhasi (O\'zbek tilida)",\n'
        '  "difficulty": "Oson" yoki "O\'rta" yoki "Murakkab",\n'
        '  "description": "Talaba bajarishi kerak bo\'lgan aniq va tushunarli vazifa matni (O\'zbek tilida)",\n'
        '  "hint": "Maslahat yoki yo\'llanma",\n'
        '  "gold_sql": "SELECT ..."\n'
        "}"
    )

    user_prompt = (
        f"Hozirgi Ma'lumotlar Bazasi Tuzilmasi va Ma'lumotlari:\n{db_context}\n\n"
        f"[Generatsiya kodi: {task_seed}]\n"
        "Iltimos, ushbu bazadagi ma'lumotlardan foydalanib, talaba uchun mutlaqo yangi, mustaqil SQL topshirig'ini tuzing."
    )

    parsed_json, used_model = call_groq_ai_json(api_key, model_name, system_prompt, user_prompt, max_tokens=800)
    if parsed_json and "gold_sql" in parsed_json:
        parsed_json["source"] = f"Groq AI ({used_model})"
        return parsed_json

    return generate_algorithmic_dynamic_task()

def generate_groq_ai_tasks_batch(count=4):
    """Generate a batch of 3-4 diverse challenges (Oson, O'rta, Murakkab) for the active database"""
    keys = get_active_ai_keys()
    db_context = get_schema_and_sample_rows()
    
    if not keys or not db_context:
        return [generate_algorithmic_dynamic_task() for _ in range(count)]

    key_row = random.choice(keys)
    api_key = key_row["api_key"]
    model_name = key_row["model_name"] or "openai/gpt-oss-120b"

    import uuid
    batch_seed = uuid.uuid4().hex[:8]

    system_prompt = (
        "Siz professional Ma'lumotlar Bazasi arxitektori va ijodkor SQL o'qituvchisisiz. "
        "Sizga foydalanuvchining faol SQLite ma'lumotlar bazasi jadvallari va namuna ma'lumotlari beriladi. "
        f"Vazifangiz: Berilgan ma'lumotlar asosida talabalar uchun {count} ta MUTLAQO YANGI, TURFA XIL DARAJADAGI (Oson, O'rta, Murakkab) va bir-birini takrorlamaydigan SQL amaliy topshiriqlari to'plamini tuzish. "
        "QAT'IY QOIDALAR:\n"
        "1. Hech qanday tayyor shablondan foydalanmang, faqat berilgan bazadagi jadvallar va ustunlar bo'yicha yangi vazifalar tuzing.\n"
        "2. Topshiriqlar turli mavzularni qamrasin (WHERE, JOIN, GROUP BY, ORDER BY, Subquery va h.k.).\n"
        "3. Har bir topshiriq uchun 'gold_sql' maydonida to'g'ri ishlaydigan SQLite SELECT kodini yozing.\n"
        "4. Javobni FAQAT toza JSON formatida quyidagi strukturada qaytaring:\n"
        "{\n"
        '  "tasks": [\n'
        '    {\n'
        '      "id": 1,\n'
        '      "title": "Topshiriq sarlavhasi",\n'
        '      "difficulty": "Oson",\n'
        '      "description": "Talaba bajarishi kerak bo\'lgan vazifa matni (O\'zbek tilida)",\n'
        '      "hint": "Maslahat yoki yo\'llanma",\n'
        '      "gold_sql": "SELECT ..."\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    user_prompt = (
        f"Faol Baza Tuzilmasi va Ma'lumotlari:\n{db_context}\n\n"
        f"[Generatsiya kodi: {batch_seed}]\n"
        f"Iltimos, ushbu baza bo'yicha {count} ta mutlaqo yangi, turli xil murakkablikdagi SQL topshiriqlarini yarating."
    )

    parsed_json, used_model = call_groq_ai_json(api_key, model_name, system_prompt, user_prompt, max_tokens=1600)
    if parsed_json and "tasks" in parsed_json:
        tasks = parsed_json.get("tasks", [])
        for t in tasks:
            t["source"] = f"Groq AI ({used_model})"
        return tasks

    return [generate_algorithmic_dynamic_task() for _ in range(count)]

@bp.route('/')
@bp.route('')
def index():
    # Ensure database is initialized
    db_path = get_user_db_path()
    if not os.path.exists(db_path):
        init_sandbox_db(db_path)
    
    schema = get_schema_dict()
    ai_keys = get_active_ai_keys()
    has_ai = len(ai_keys) > 0
    
    return render_template("student/sql_lab.html", schema=schema, sample_queries=DEFAULT_SAMPLE_QUERIES, has_ai=has_ai)

@bp.route('/api/execute', methods=['POST'])
def execute_sql():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"success": False, "error": "So'rov matni bo'sh bo'lishi mumkin emas."})
    
    blocked_keywords = ['ATTACH', 'DETACH', 'PRAGMA database_list']
    for kw in blocked_keywords:
        if kw.lower() in query.lower():
            return jsonify({"success": False, "error": f"'{kw}' operatsiyasini bajarish taqiqlangan."})
    
    conn = get_db_connection()
    c = conn.cursor()
    
    start_time = time.time()
    try:
        c.execute(query)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        if c.description:
            columns = [desc[0] for desc in c.description]
            rows = [list(row) for row in c.fetchall()]
            conn.close()
            return jsonify({
                "success": True,
                "is_select": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "time_ms": duration_ms
            })
        else:
            conn.commit()
            rows_affected = c.rowcount
            conn.close()
            return jsonify({
                "success": True,
                "is_select": False,
                "message": "So'rov muvaffaqiyatli bajarildi. O'zgarishlar kiritildi.",
                "rows_affected": rows_affected,
                "time_ms": duration_ms
            })
    except Exception as e:
        conn.close()
        return jsonify({
            "success": False,
            "error": str(e)
        })

@bp.route('/api/reset', methods=['POST'])
def reset_db():
    db_path = get_user_db_path()
    try:
        init_sandbox_db(db_path, DEFAULT_SCHEMA_SQL)
        return jsonify({
            "success": True,
            "message": "Standart ma'lumotlar bazasi tiklandi.",
            "schema": get_schema_dict(),
            "sample_queries": DEFAULT_SAMPLE_QUERIES
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ================= AI DATABASE & SCHEMA GENERATION =================
@bp.route('/api/ai-generate-database', methods=['POST'])
def api_ai_generate_database():
    data = request.get_json() or {}
    domain_hint = data.get('domain', None)

    # 1. Generate scenario with AI
    scenario = generate_ai_database_scenario(domain_hint)
    schema_sql = scenario.get("schema_sql", "")

    if not schema_sql:
        return jsonify({"success": False, "error": "AI ma'lumotlar bazasi sxemasini yarata olmadi."})

    # 2. Apply generated schema in student sandbox
    db_path = get_user_db_path()
    try:
        init_sandbox_db(db_path, schema_sql)
        updated_schema = get_schema_dict()

        return jsonify({
            "success": True,
            "domain_name": scenario.get("domain_name", "Yangi AI Ma'lumotlar Bazasi"),
            "description": scenario.get("description", ""),
            "source": scenario.get("source", "Groq AI"),
            "schema": updated_schema,
            "sample_queries": scenario.get("sample_queries", []),
            "tasks": scenario.get("tasks", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Sxemani bazaga kiritishda xatolik: {str(e)}"})

# ================= AI DYNAMIC TASK GENERATORS =================
@bp.route('/api/ai-generate-task', methods=['POST'])
def api_ai_generate_task():
    task = generate_groq_ai_task()
    return jsonify({"success": True, "task": task})

@bp.route('/api/ai-generate-tasks-batch', methods=['POST'])
def api_ai_generate_tasks_batch():
    tasks = generate_groq_ai_tasks_batch(4)
    return jsonify({"success": True, "tasks": tasks})

@bp.route('/api/ai-check-task', methods=['POST'])
def api_ai_check_task():
    data = request.get_json() or {}
    user_query = data.get('query', '').strip()
    gold_sql = data.get('gold_sql', '').strip()

    if not user_query:
        return jsonify({"success": False, "error": "Iltimos, avval SQL so'rovingizni yozing."})
    if not gold_sql:
        return jsonify({"success": False, "error": "AI javob namunasi mavjud emas."})

    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute(user_query)
        user_rows = [list(r) for r in c.fetchall()]

        c.execute(gold_sql)
        gold_rows = [list(r) for r in c.fetchall()]

        conn.close()

        is_match = (user_rows == gold_rows) or (sorted([str(x) for x in user_rows]) == sorted([str(x) for x in gold_rows]))

        if is_match and len(gold_rows) > 0:
            return jsonify({
                "success": True,
                "correct": True,
                "message": "🎉 Qoyilmaqom! AI topshirig'ini 100% to'g'ri bajardingiz!",
                "row_count": len(user_rows)
            })
        elif is_match and len(gold_rows) == 0 and len(user_rows) == 0:
            return jsonify({
                "success": True,
                "correct": True,
                "message": "✅ So'rov muvaffaqiyatli bajarildi (0 ta qator)."
            })
        else:
            return jsonify({
                "success": True,
                "correct": False,
                "message": f"Natijalar mos kelmadi. Sizning so'rovingiz {len(user_rows)} ta qator qaytardi, kutilgan natija esa {len(gold_rows)} ta qator.",
                "hint_available": True
            })
    except Exception as e:
        conn.close()
        return jsonify({
            "success": False,
            "error": f"SQL xatolik: {str(e)}"
        })
