# Instalação (oficina local + cloud)

A app corre em **dois sítios**, com o **mesmo código** (muda só `FT_ROLE`):

```
  TABLET ──LAN──> SERVIDOR LOCAL (oficina, FT_ROLE=oficina)  ← master da operação
                        │  sync (quando há internet)
                        ▼
                  CLOUD (FT_ROLE=cloud)  ← site público + portal do cliente + marcações
```

O servidor local funciona **sem internet** (o tablet só precisa da LAN). A sincronização
recupera sozinha quando a internet volta (marca de água — nada se perde).

---

## 1. Cloud (site + portal + marcações)

Mais fácil no **Render** (Postgres incluído). Liga o repositório e define:

- **Build:** `./build.sh` · **Start:** `gunicorn fulltorque.wsgi`
- **Variáveis** (ver `.env.example`):
  - `FT_ROLE=cloud`
  - `DJANGO_SECRET_KEY=...` · `DJANGO_DEBUG=False`
  - `DJANGO_ALLOWED_HOSTS=o-teu-dominio.onrender.com`
  - `DJANGO_CSRF_TRUSTED_ORIGINS=https://o-teu-dominio.onrender.com`
  - `DATABASE_URL=...` (Postgres do Render)
  - `SYNC_API_KEY=<chave-secreta-partilhada>` (a MESMA no local)
  - Fotos: `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
    `AWS_S3_ENDPOINT_URL`, `AWS_S3_CUSTOM_DOMAIN` (Cloudflare R2)

---

## 2. Servidor local da oficina (Docker)

Num mini-PC sempre ligado, na rede da oficina. Precisa só de Docker.

```bash
cp .env.example .env      # preenche SECRET_KEY, SYNC_API_KEY, SYNC_CLOUD_URL
docker compose up -d --build
```

`.env` mínimo para o local:
```
DJANGO_SECRET_KEY=<chave-longa>
DB_PASSWORD=<password-postgres>
SYNC_API_KEY=<a-MESMA-chave-da-cloud>
SYNC_CLOUD_URL=https://o-teu-dominio.onrender.com
SEED_DEMO=0            # 1 só para encher com dados de demonstração
```

- O tablet liga-se a **`http://<ip-do-servidor>/`** pela LAN (deixa esse tablet sem net).
- O serviço `sync` envia/puxa da cloud a cada `SYNC_INTERVALO` segundos (omissão 120).
- Catálogo de marcas/modelos é semeado automaticamente. Cria o **Local**, os
  **funcionários** e os **PINs** no admin (`/admin/`).

> O tablet do funcionário **não precisa de internet** — só de chegar ao servidor local.

---

## 3. Backups (servidor local)

```bash
# cópia da base de dados
docker compose exec db pg_dump -U fulltorque fulltorque > backup_$(date +%F).sql
# fotos
docker run --rm -v fulltorque_media:/m -v "$PWD":/out alpine tar czf /out/media_$(date +%F).tgz -C /m .
```
Agenda isto (cron) e guarda as cópias fora da máquina.

---

## Testar a sincronização localmente (sem hardware)

```bash
# "cloud" numa 2ª base de dados, porta 8001
DATABASE_URL="sqlite:///$(pwd)/db_cloud.sqlite3" FT_ROLE=cloud SYNC_API_KEY=test \
  .venv/bin/python manage.py migrate
DATABASE_URL="sqlite:///$(pwd)/db_cloud.sqlite3" FT_ROLE=cloud SYNC_API_KEY=test \
  .venv/bin/python manage.py runserver 8001

# sincronizar a oficina (BD principal) com a "cloud"
SYNC_API_KEY=test .venv/bin/python manage.py sync_cloud --cloud-url http://127.0.0.1:8001 --key test
```
