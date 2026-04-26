# Online gaan — checklist

Dit is een **technische** deploy-checklist. Geen fiscaal of RVO/WBSO-advies; zie onderaan.

## 1. Omgeving (hosting)

- Python 3.12 (of 3.11+)
- Eén instance met **persistent volume** of schijf voor `data/users.csv` als je abonnees niet wilt verliezen bij redeploy, **of** later overstappen op een database (meerdere servers = geen gedeeld CSV; dan Redis + DB inrichten)
- `APP_ENV=production`
- `SECRET_KEY` — willekeurig, lang, geen default
- `PORT` meestal door platform gezet; anders 5000

**Starten:** `waitress-serve --listen=0.0.0.0:$PORT wsgi:app` (of via `Procfile` / `Dockerfile`).

**Render (PaaS):** build `pip install -r requirements.txt`, start o.a. `gunicorn wsgi:app --bind 0.0.0.0:$PORT` — de app draait via **`wsgi.py`** (`app = create_app()`), **niet** `gunicorn app:app` (geen globale `app` in `app.py`). `requirements.txt` bevat o.a. **gunicorn**; `templates/index.html` is **niet** nodig: er is geen `/` met Jinja; admin gebruikt `templates/admin_dashboard.html` op `/admin/dashboard`. Root `GET /` = JSON-hello.

## 2. Netwerk

- Publiceer **alleen** achter **HTTPS** (reverse proxy of platform-TLS)
- Je frontend-domein moet in `CORS` staan; aanpassen in `config.py` of later via env (nu: `jmcovenant.nl` + www + staging + localhost)

## 3. Stripe (betaald)

- **Live**-keys: `STRIPE_SECRET_KEY` = `sk_live_...` (niet `sk_test_` in productie)
- `STRIPE_PRICE_ID` = live prijs-ID uit Stripe
- `STRIPE_WEBHOOK_SECRET` = `whsec_...` van het **live**-webhook-eindpunt
- **Webhook-URL in Stripe (live):** `https://<jouw-api-domein>/billing/webhook`
- Gebeurtenissen minimaal: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
- `FRONTEND_BASE_URL` = `https://jmcovenant.nl` (of je echte success/cancel-URL)
- `INTERNAL_API_KEY` = sterk, voor `POST /billing/status` (frontend/server-side calls)

**Testflow:** testbetaling in live modus (klein bedrag) → webhook ontvangt → in `data/users.csv` `is_paid=1` voor dat e-mailadres

## 4. PDS (opslag)

- `generated_pds/` moet op de server **schrijfbaar** blijven
- Periodiek legen of volume-limiet, anders vult de schijf

## 4b. Eventlog (auditspoor, minimaal)

- Append-only **`data/events.jsonl`** (één JSON-object per regel, schema `v=1`). Uit: o.a. `pds.*`, `billing.stripe.*`.
- **Actor** is standaard **HMAC(SECRET_KEY, e-mail)** — geen leesbare e-mail in het log, tenzij `EVENT_LOG_PLAIN_EMAIL=1` (meestal alleen lokaal).
- Zelfde regels als `users.csv`: **back-up** op persistent volume, of later stream naar een echte logstack.
- Uit: `EVENT_LOG_ENABLED=0` schakelt alles uit; `EVENT_LOG_PATH` overschrijft bestandspad.

## 5. Gezondheid

- `GET /health` — voor uptime-monitoring
- `GET/POST` op `/billing/webhook` — alleen POST met Stripe-handtekening; monitor geen 500s

## 6. RVO / WBSO — binnen de regels, fouten vermijden

- **Dit bestand** beschrijft **operatie** (hosting, betaling, API). Dat is **geen** fiscale beoordeling; “online staan” zegt op zich niets over WBSO of een RVO-regeling.
- **WBSO** en **RVO** toets je met een **fiscaal adviseur** op basis van *werkzaamheden, uren, projecten en de voorwaarden van die regeling* — goed aansluiten = **binnen de kaders** blijven en **dure fouten of discussie met de fiscus** beperken.
- Praktisch: houd in je administratie **S&O / ontwikkelwerk** duidelijk **gescheiden** van **exploitatie, verkoop en routinematig onderhoud** (wat daar ook voor jullie geldt) — en stem dat af op je adviseur, niet op trucs in code.
- Bedoeling is: **fouten vermijden door netjes te voldoen** (onderbouwing, reële uren, juiste omschrijving). Geen **poging om regels te “verbergen” in software**; dat lost fiscale zorg niet op en vormt juist **extra risico**.

## 7. Nog van jou (invullen)

- Domein/SSL voor API: `https://api.jmcovenant.nl/...` ofzelfde host als static — exact pad voor webhook
- E-mail/communicatie wanneer betaling faalt
- Back-up van `data/users.csv` of migratiepad naar database

Als de API op een **ander domein** draait, zet `CORS_EXTRA_ORIGINS=https://jouw-frontend` (of meerdere, komma’s) in de server-`env` — zie `config.py`.
