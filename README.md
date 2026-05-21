# 🎓 Түркістан жоғары көп салалы қол өнер колледжі
## Оқытушылар ғылыми-әдістемелік жетістіктері рейтингі

Оқытушылардың ғылыми-әдістемелік жетістіктерін тіркейтін және рейтингін есептейтін толық жұмыс істейтін веб-сайт.

**Технологиялар:**
- 🗃️ **Дерекқор:** Microsoft SQL Server (SSMS)
- 🐍 **Backend:** Python 3.10+ / Flask 3
- 🎨 **Frontend:** HTML + CSS3 (Glassmorphism) + JavaScript (vanilla) + Chart.js + tsParticles
- 🌐 **Көпсайт:** қазақша / орысша / ағылшынша (i18n)

---

## 📋 Функционал

### Оқытушыға:
- ✅ Жеке кабинет (логин / пароль)
- ✅ Жетістік қосу (сурет / құжат жүктеу)
- ✅ Өз жетістіктерінің статусын көру
- ✅ Рейтинг, badge, прогресс бар
- ✅ Басқа оқытушыларға жұлдызшамен баға беру + пікір қалдыру

### Админға:
- ✅ Жетістіктерді қарау (суретпен)
- ✅ Checkbox арқылы топтық растау
- ✅ Жеке растау / қабылдамау (себебімен)
- ✅ Оқытушы қосу / өшіру
- ✅ Барлық оқиғалар тарихы (audit log)

### Қоғамдық:
- ✅ Басты бет — барлық оқытушылар карточкасы
- ✅ **Топ-3 подиум** (алтын/күміс/қола) — анимациялы
- ✅ Нақты уақыттағы іздеу (live search dropdown)
- ✅ **Dashboard** — Chart.js диаграммалары (Bar, Pie, Line)
- ✅ Оқытушы профилі: жетістіктер + badge + прогресс + пікірлер
- ✅ **Dark / Light тақырып** (localStorage)
- ✅ **Көп тіл** — KZ / RU / EN
- ✅ Мобильді дизайн (responsive)
- ✅ Анимациялар: tsParticles фоны, glassmorphism, counter, confetti-style

---

## 📂 Жоба құрылымы

```
tapsyrma/
├── database.sql            # T-SQL — барлық кестелер, триггер, процедуралар
├── app.py                  # Flask сервері (барлық маршруттар)
├── config.py               # SQL Server connection параметрлері
├── db.py                   # pyodbc қабаты
├── requirements.txt        # Python пакеттер
├── README.md
├── templates/              # Jinja2 шаблондары
│   ├── base.html
│   ├── index.html          # Басты бет (карточкалар + подиум)
│   ├── login.html
│   ├── profile.html        # Оқытушының жеке кабинеті
│   ├── teacher_profile.html# Қоғамдық профиль
│   ├── admin.html          # Админ панелі
│   ├── admin_teachers.html # Оқытушылармен басқару
│   ├── dashboard.html      # Диаграммалар
│   ├── 404.html
│   └── 500.html
└── static/
    ├── css/style.css       # Glassmorphism дизайн
    ├── js/main.js          # Анимациялар, іздеу, тақырып
    ├── js/i18n.js          # Тілдер сөздігі
    └── uploads/            # Жүктелген суреттер
```

---

## 🚀 Орнату қадамдары

### 1️⃣ Алғышарттар

- Windows 10/11 (немесе SQL Server бар кез келген ОЖ)
- **Microsoft SQL Server** + **SQL Server Management Studio (SSMS)** орнатылған болуы керек
- **Python 3.10+** ([python.org](https://www.python.org/downloads/) арқылы жүктеу)
- **ODBC Driver 17 for SQL Server** — [жүктеу сілтемесі](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### 2️⃣ Дерекқорды жасау (SSMS-те)

1. SSMS-ті ашыңыз → өз SQL Server серверіне қосылыңыз
2. File → Open → File → `database.sql` файлын ашыңыз
3. **F5** басыңыз (немесе Execute)
4. Хабарлама: `✅ tapsyrma дерекқоры сәтті құрылды!`

Төмендегі объектілер автоматты жасалады:
- **Кестелер:** `Admins`, `Teachers`, `AchievementTypes`, `Achievements`, `Badges`, `TeacherBadges`, `Reviews`, `Events`, `AuditLog`
- **Триггер:** `trg_UpdateTeacherScore` (ұпайды автоматты қайта есептейді)
- **Процедуралар:** `sp_ApproveAchievement`, `sp_RejectAchievement`
- **View:** `vw_TeacherRating`, **Function:** `fn_GetTopTeachers`

### 3️⃣ Connection string баптау

`config.py` ішіндегі `SQL_SERVER` мәнін өз серверіңіздің атына өзгертіңіз.

**Сервер атын табу:**
- SSMS-те Server Name қатарын көріңіз
- Жиі кездесетін мысалдар:
  - `localhost\SQLEXPRESS` (SQL Server Express)
  - `DESKTOP-XXXX\SQLEXPRESS`
  - `(local)` немесе `.` (толық SQL Server)
  - `.\SQLEXPRESS`

```python
SQL_SERVER = r"localhost\SQLEXPRESS"   # ← өзіңіздің серверіңіз
SQL_DATABASE = "tapsyrma"
USE_TRUSTED = True                     # Windows аутентификациясы
```

**SQL Server аутентификациясын қолдансаңыз:**
```python
USE_TRUSTED = False
SQL_USER = "sa"
SQL_PASSWORD = "your_password"
```

### 4️⃣ Python ортасын орнату

PowerShell-де жоба қалтасына өтіңіз:

```powershell
cd c:\Users\Студент\Documents\tapsyrma
```

Виртуалды ортаны жасау (ұсынылады):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> ⚠️ Егер PowerShell script execution policy қатесі болса:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

Тәуелділіктерді орнату:

```powershell
pip install -r requirements.txt
```

### 5️⃣ Серверді іске қосу

```powershell
python app.py
```

Нәтиже:

```
============================================================
  Түркістан колледжі — Оқытушылар рейтингі
============================================================
✅ SQL Server байланысы сәтті
✅ Әдепкі парольдер орнатылды (admin/admin123, oq./teacher123)
============================================================
  🚀 Сервер: http://localhost:5000
============================================================
```

Браузерден ашыңыз: **http://localhost:5000**

---

## 🔐 Тест аккаунттар

Сайт алғаш рет іске қосылғанда парольдер автоматты орнатылады:

| Рөл         | Логин      | Пароль        |
|:------------|:-----------|:--------------|
| 👑 Админ    | `admin`    | `admin123`    |
| 👨‍🏫 Оқытушы | `aigul`    | `teacher123`  |
| 👨‍🏫 Оқытушы | `nurlan`   | `teacher123`  |
| 👨‍🏫 Оқытушы | `dinara`   | `teacher123`  |
| 👨‍🏫 Оқытушы | `erlan`    | `teacher123`  |
| 👨‍🏫 Оқытушы | `madina`   | `teacher123`  |
| 👨‍🏫 Оқытушы | `askhat`   | `teacher123`  |

---

## 🎯 Қалай пайдалану

### Оқытушы ретінде:

1. **Логин:** `http://localhost:5000/login` → Оқытушы → `aigul` / `teacher123`
2. **Профиль:** жеке кабинетіңізге өтеді
3. **Фото өзгерту:** профильдегі аватарға басыңыз
4. **Жетістік қосу:**
   - Түрін таңдаңыз (Халықаралық, Республикалық, т.б.)
   - Атауын жазыңыз
   - Сипаттама (міндетті емес)
   - Растайтын құжатты немесе суретті жүктеңіз
   - Жіберу
5. Жетістік "Күтілуде" статусымен админге көрсетіледі

### Админ ретінде:

1. **Логин:** `http://localhost:5000/login` → Админ → `admin` / `admin123`
2. **Админ панелі:** тексерілмеген жетістіктер тізімі
3. **Растау жолдары:**
   - ✅ Бір басу — жеке растау
   - ❌ — қабылдамау (себебін көрсетіңіз)
   - ☑️ Checkbox + төмендегі жасыл "Сақтау" — топтық растау
4. Растау кезінде:
   - `sp_ApproveAchievement` процедурасы шақырылады
   - Оқытушының ұпайы автоматты жаңарады (триггер арқылы)
   - Жаңа badge-тер автоматты беріледі

### Кез келген қолданушы:

- 🏠 Басты бет: барлық оқытушылар + Топ-3 подиум + іздеу
- 📊 `/dashboard`: Chart.js диаграммалар
- 👨‍🏫 Оқытушының картасына басу → қоғамдық профилі
- 🌙 Оң жақтағы айды басу → Dark/Light режим
- 🌐 Globe иконкасы → KZ / RU / EN тілдері
- 🔍 Іздеу жолағына жазу → live search dropdown

---

## 🗃️ Дерекқор құрылымы

### Негізгі кестелер

```sql
Admins
├── AdminId, Username, PasswordHash, FullName

Teachers
├── TeacherId, FullName, PhotoPath, Login, PasswordHash,
│   Department, Position, Email, TotalScore

AchievementTypes
├── TypeId, TypeName, Score, Category
│   (Халықаралық=10, Республикалық=8, Облыстық=6, ...)

Achievements
├── AchievementId, TeacherId, TypeId, Title, Description,
│   ImagePath, IsApproved, IsRejected, RejectReason,
│   Score, SubmittedAt, ApprovedAt

Badges
├── BadgeId, BadgeName, MinScore, Icon, Color
│   (Үміткер 10+, Белсенді 30+, Үздік 60+, Шебер 100+, Легенда 150+)
```

### Триггер — автоматты ұпай

`trg_UpdateTeacherScore` — `Achievements.IsApproved` өзгергенде `Teachers.TotalScore` қайта есептеледі.

### Процедура — растау

```sql
EXEC sp_ApproveAchievement @AchievementId = 5;
```

- `Achievements.IsApproved = 1`, `Score` орнатады
- Жаңа badge-тер автоматты беріледі

---

## 🐛 Жиі кездесетін қателер

### ❌ `[Microsoft][ODBC Driver Manager] Data source name not found`

**Шешім:** ODBC Driver 17 for SQL Server орнатыңыз:
[https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### ❌ `[08001] Named Pipes Provider: Could not open a connection to SQL Server`

**Шешім:**
1. SQL Server Configuration Manager ашыңыз
2. SQL Server Network Configuration → Protocols → **TCP/IP** → Enable
3. SQL Server қызметін қайта іске қосыңыз

### ❌ `Login failed for user`

**Шешім:** `config.py` ішіндегі `USE_TRUSTED` / `SQL_USER` / `SQL_PASSWORD` дұрыс екенін тексеріңіз.

### ❌ `pyodbc` орнатылмайды

**Шешім:** Visual C++ Build Tools керек болуы мүмкін:
```powershell
pip install --upgrade setuptools wheel
pip install pyodbc
```

### ❌ Парольдер жұмыс істемейді

SSMS-те мына сұранысты орындаңыз:
```sql
SELECT Username, PasswordHash FROM tapsyrma.dbo.Admins;
```

Егер `PasswordHash` "PLACEHOLDER..." болса, `python app.py` қайта іске қосыңыз — автоматты орнатылады.

---

## 📝 Өзгертулер енгізу

### Жаңа жетістік түрі қосу

SSMS-те:

```sql
INSERT INTO AchievementTypes (TypeName, Score, Category)
VALUES (N'Жаңа түр', 5, N'Категория');
```

### Жаңа оқытушыны бастапқы парольмен қосу (SSMS арқылы)

Оқытушыларды `/admin/teachers` бетінен қосқан дұрыс (парольді автоматты hash жасайды). Бірақ SSMS арқылы қосқыңыз келсе, python-да hash генерациялап қойыңыз:

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("my_password"))
```

Содан кейін SSMS-те:

```sql
INSERT INTO Teachers (FullName, Login, PasswordHash, Department)
VALUES (N'Аты-жөні', 'login', 'hash_осында', N'Бөлім');
```

---

## 🔒 Қауіпсіздік ескертпелері

Өнімді ортада міндетті:
- [ ] `SECRET_KEY`-ді өзгерту (`config.py`)
- [ ] `FLASK_ENV=production` қою
- [ ] HTTPS қолдану (nginx + letsencrypt)
- [ ] `app.run(debug=False)` қою
- [ ] Rate limiting қосу (Flask-Limiter)
- [ ] Admin парольдерді күрделілендіру

Дерекқор жағында:
- ✅ Parameterized queries (SQL Injection қорғанысы)
- ✅ Hash-талған парольдер (`werkzeug bcrypt-like`)
- ✅ Stored Procedures бойынша кіру
- ✅ Audit log

---

## 📜 Лицензия

Колледждің ішкі пайдалануы үшін жасалған оқу жобасы.

---

## 👨‍💻 Қосымша функциялар (келешекте)

Келесі функцияларды қосуға болады:
- 📱 PWA (offline режим)
- 📧 Email хабарламалар (nodemailer / smtplib)
- 📄 PDF есептер (ReportLab)
- 🎓 Сертификат генератор (jsPDF)
- 🔔 Real-time хабарламалар (Socket.io)
- 📅 Іс-шаралар күнтізбесі (FullCalendar.js)
- 📊 Оқытушыларды салыстыру (Radar chart)
- 🖨️ Excel / Word экспорт (openpyxl / python-docx)

---

**🎉 Сәтті қолдануға тілектіміз!**
