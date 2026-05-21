# Railway деплой (PostgreSQL)

## 1. GitHub

Репозиторий: код `tapsyrma/` қалтасында.

## 2. Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Репозиторийті таңдаңыз, **Root Directory** (қажет болса): `tapsyrma`
3. **+ New** → **Database** → **PostgreSQL**
4. PostgreSQL сервисінде **Variables** → `DATABASE_URL` көшіріңіз
5. Web сервисінде **Variables**:
   - `DATABASE_URL` = PostgreSQL-тен (Reference немесе көшірме)
   - `SECRET_KEY` = кездейсоқ ұзын мәтін

## 3. Build

Railway автоматты:
- `requirements.txt` (psycopg2-binary, gunicorn)
- `Procfile`: `web: gunicorn wsgi:app`

## 4. Дерекқор (бір рет)

Web сервис → **Settings** → Shell немесе локальді:

```bash
python setup_db.py
```

## 5. Домен

**Settings** → **Generate Domain** → `https://xxx.up.railway.app`

## Локальді тест

`.env`:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/tapsyrma
SECRET_KEY=dev-secret
```

```powershell
pip install -r requirements.txt
python setup_db.py
python app.py
```

## Тест логиндер

- `admin` / `admin123`
- `aigul` / `teacher123`
