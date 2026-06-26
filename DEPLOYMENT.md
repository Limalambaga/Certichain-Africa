# Déployer Certichain Africa en production

## Pourquoi pas juste "héberger le dossier tel quel" ?

Ton app tourne actuellement avec `python app.py`, qui démarre le **serveur de
développement Flask** — il n'est pas conçu pour de vrais utilisateurs (lent,
une seule requête à la fois, plante sous charge). En production, on utilise
**Gunicorn** (déjà ajouté à `requirements.txt` et `Procfile`) comme serveur
WSGI réel.

Deuxième point critique : ta base de données est actuellement un fichier
**SQLite** (`instance/certichain.db`). Sur la plupart des plateformes
d'hébergement gratuites, le disque est **éphémère** — il est effacé à chaque
redéploiement ou redémarrage. **Tu perdrais toutes tes institutions et
certificats.** Il faut migrer vers une base de données managée (PostgreSQL)
avant de déployer.

---

## Option recommandée : Render.com (gratuit, le plus simple)

### Étape 1 — Créer la base PostgreSQL

1. Va sur [render.com](https://render.com), crée un compte (gratuit)
2. **New +** → **PostgreSQL** → choisis un nom, région la plus proche (Europe)
3. Une fois créée, copie l'**Internal Database URL** (commence par `postgresql://`)

### Étape 2 — Créer le service web

1. **New +** → **Web Service**
2. Connecte ton dépôt GitHub `Certichain-Africa`
3. Render détecte Python automatiquement. Renseigne :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Plan : **Free**

### Étape 3 — Variables d'environnement

Dans l'onglet **Environment** du service, ajoute **toutes** les variables de
ton `.env` local, une par une (Render ne lit jamais ton `.env`, qui n'est
même pas poussé sur GitHub) :

```
SECRET_KEY=                  ← génère une nouvelle valeur aléatoire, ne réutilise pas celle du dev
APP_BASE_URL=https://ton-app.onrender.com
FLASK_DEBUG=False
DATABASE_URL=                ← colle l'Internal Database URL de l'étape 1
ADMIN_EMAIL=
ADMIN_PASSWORD=              ← choisis un VRAI mot de passe fort, pas "ChangeMe123!"
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
PINATA_API_KEY=
PINATA_SECRET_KEY=
INFURA_PROJECT_ID=
POLYGON_RPC=https://polygon-bor-rpc.publicnode.com
ISSUER_ADDRESS=
ISSUER_PRIVATE_KEY=
CONTRACT_ADDRESS=
MOMO_SUBSCRIPTION_KEY=
MOMO_API_USER=
MOMO_API_KEY=
MOMO_ENVIRONMENT=
MOMO_BASE_URL=
MOMO_CALLBACK_URL=
```

> **Important sécurité :** génère un nouveau `SECRET_KEY` pour la production
> avec : `python -c "import secrets; print(secrets.token_hex(32))"`

### Étape 4 — Déployer

Clique **Create Web Service**. Render installe les dépendances, lance
Gunicorn, et te donne une URL publique (`https://ton-app.onrender.com`) en
quelques minutes.

### Étape 5 — Vérifier

- Ouvre l'URL publique → la landing page doit s'afficher
- Va sur `/admin/login` → connecte-toi avec `ADMIN_EMAIL`/`ADMIN_PASSWORD`
- Crée un compte institution de test, génère un certificat

---

## Limite importante à connaître : les fichiers PDF

Les PDF générés sont actuellement écrits sur le disque local
(`certs/uploads/`). Sur Render free tier, **ce dossier est effacé à chaque
redéploiement**. Bonne nouvelle : ton code a déjà un mécanisme de
**régénération automatique** — si le PDF local est manquant, l'app le
recrée à la volée à partir des données en base (déjà en place dans
`download_certificate_file` et maintenant aussi dans l'envoi par email).
Le hash IPFS, lui, reste permanent indépendamment du disque.

Pour un vrai usage en production à long terme, ajoute un **disque
persistant Render** (payant, ~7$/mois) sous l'onglet **Disks** du service,
monté sur `/opt/render/project/src/certs`.

---

## Alternative : Railway.app

Même principe que Render, interface différente :

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. **New** → **Database** → **PostgreSQL** (ajouté automatiquement au projet)
3. Railway expose automatiquement `DATABASE_URL` dans les variables du service web — pas besoin de copier-coller
4. Ajoute les autres variables d'environnement manuellement (Settings → Variables)
5. Railway détecte le `Procfile` automatiquement

---

## Checklist avant de pousser en production

- [ ] `SECRET_KEY` régénéré (différent de celui du `.env` local)
- [ ] `ADMIN_PASSWORD` changé pour un mot de passe fort unique
- [ ] `FLASK_DEBUG=False` (jamais `True` en production — risque de RCE via le débogueur Flask)
- [ ] `DATABASE_URL` pointe vers PostgreSQL managé, pas SQLite
- [ ] Le wallet `ISSUER_ADDRESS` a assez de MATIC (vérifie via `/api/blockchain/status`)
- [ ] `.env` n'est PAS commité sur GitHub (déjà dans `.gitignore`, à vérifier)
