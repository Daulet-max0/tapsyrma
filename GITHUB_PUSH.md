# GitHub push (логин: Admin1)

Локально уже выполнено:

```text
git init
git add .
git commit -m "Railway deploy: Flask + PostgreSQL"
git branch -M main
git remote add origin https://github.com/Admin1/tapsyrma.git
```

## Создайте репозиторий на GitHub (один раз)

1. Откройте: https://github.com/new?name=tapsyrma  
2. Owner: **Admin1** (ваш аккаунт)  
3. **Create repository** (без README — код уже в коммите)

## Push

```powershell
cd C:\Users\Admin1\Documents\tapsyrma\tapsyrma
git push -u origin main
```

При запросе входа — **GitHub login** + **Personal Access Token** (не пароль от сайта).

Токен: GitHub → Settings → Developer settings → Personal access tokens.

## Проверка

https://github.com/Admin1/tapsyrma
