## Infotherapy Club Website (UI/UX Phase)

This is the initial UI/UX implementation for the Infotherapy AI SW club website using Flask, HTML, CSS, and JavaScript. Backend integrations (Firebase Auth/Firestore, AWS deployment) will come next.

### Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### Structure

- `app.py` - Flask app and routes
- `templates/` - Jinja2 templates (`base.html`, `index.html`, `login.html`, `signup.html`, `learn.html`)
- `static/css/main.css` - Toss-like white/blue theme
- `static/js/main.js` - Minimal interactions (mobile nav, form submit loading)
- `invites.json` - 초대 목록(이름+코드+optional admin)

### Next Steps

- Integrate Firebase Auth (email/password with invite code gate)
- Firestore for materials and assignments CRUD
- Session management and route protection
- AWS deployment (Elastic Beanstalk or EC2 + Nginx/Gunicorn)

### Invites (이름+코드 JSON)

`invites.json` 예시:

```json
[
  { "name": "홍길동", "code": "INF-2025-001", "admin": true },
  { "name": "김철수", "code": "INF-2025-002" }
]
```

회원가입 시 입력한 이름과 코드가 이 파일과 일치해야 가입됩니다. `admin: true`가 있으면 관리자 권한으로 저장됩니다.

### Firebase setup (fix credentials error)

Use ONE of the two options:

1) Service account (recommended for prod)

- Download a service account JSON from Google Cloud Console.
- Create `.env` in project root:

```env
FLASK_SECRET=change-me
GOOGLE_APPLICATION_CREDENTIALS=C:\\absolute\\path\\to\\serviceAccount.json
FIREBASE_PROJECT_ID=your-project-id

# Client Firebase config for login/signup pages
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...
```

2) Local emulators (dev)

```powershell
npm i -g firebase-tools
firebase login
firebase init emulators   # select auth, firestore
firebase emulators:start --only auth,firestore
```

And set `.env`:

```env
FLASK_SECRET=change-me
FIREBASE_PROJECT_ID=demo-infotherapy
FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
```


