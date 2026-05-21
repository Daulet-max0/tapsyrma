# PythonAnywhere-ке жариялау (tapsyrma)

## 1. MySQL дерекқоры (PythonAnywhere)

1. [pythonanywhere.com](https://www.pythonanywhere.com) → **Databases**
2. **Create database** → аты: `tapsyrma`
3. Жазып алңыз:
   - **Host:** `ВАШ_ЛОГИН.mysql.pythonanywhere-services.com`
   - **User:** `ВАШ_ЛОГИН`
   - **Password:** (Databases бетіндегі пароль)
   - **Database name:** `ВАШ_ЛОГИН$tapsyrma` ← **`$` міндетті!**

## 2. Кодты жүктеу

**Bash console** (PythonAnywhere):

```bash
cd ~
git clone https://github.com/СІЗДІҢ_РЕПО.git tapsyrma
# немесе Files вкладкасы арқылы tapsyrma/tapsyrma қалтасын жүктеңіз
cd ~/tapsyrma/tapsyrma
pip install --user -r requirements.txt
```

## 3. `.env` файл

```bash
cd ~/tapsyrma/tapsyrma
cp .env.example .env
nano .env
```

Мысал (логин `student123`):

```env
PYTHONANYWHERE=1
DB_HOST=student123.mysql.pythonanywhere-services.com
DB_USER=student123
DB_PASSWORD=пароль_Databases_бетінен
DB_NAME=student123$tapsyrma
SECRET_KEY=кездейсоқ_ұзын_құпия_кілт
```

## 4. Кестелерді орнату

```bash
cd ~/tapsyrma/tapsyrma
python setup_db.py
```

## 5. Web app (WSGI)

1. **Web** → **Add a new web app** → Manual configuration → Python 3.12
2. **Code** → WSGI file → `wsgi.py` жолын көрсетіңіз:
   `/home/ВАШ_ЛОГИН/tapsyrma/tapsyrma/wsgi.py`
3. `wsgi.py` ішінде `YOURUSERNAME` → өз логиніңіз
4. **Static files:**
   - URL: `/static/`
   - Directory: `/home/ВАШ_ЛОГИН/tapsyrma/tapsyrma/static/`
5. **Reload** батырмасын басыңыз

Сайт: `https://ВАШ_ЛОГИН.pythonanywhere.com`

## Локальді компьютерде қате шықса

Бұл қалыпты: жергілікті MySQL жоқ болса, сайт тек **PythonAnywhere**-те жұмыс істейді. Локальді тест үшін XAMPP MySQL қосып, `.env` локальді мәндермен қолданыңыз.

## Тест логиндер

- Админ: `admin` / `admin123`
- Оқытушы: `aigul` / `teacher123`
