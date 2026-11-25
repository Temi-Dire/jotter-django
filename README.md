# Jotter: Django registration, login, dashboard and email OTP

This is the `mysite` project with the `core` app from class, with the assignment added:

1. **Registration and login.** Sign up with name, username, email and password. Log in with either your username or your email.
2. **User dashboard.** Only verified, logged-in users can see it. It shows your profile and your posts, and lets you write new ones.
3. **Email verification with an OTP code.** After signing up you get a 6-digit code by email. You can't reach the dashboard until you enter it.

## Run it (Windows)

```
cd jennifer-django
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000.

On Mac/Linux, use `source venv/bin/activate` instead of `venv\Scripts\activate`.

## Where the OTP code goes

While testing, emails are **printed in the terminal** where `runserver` is running. Look for a line like:

```
Your verification code is: 482913
```

To send real emails with Gmail:

1. Turn on 2-step verification on the Gmail account, then create an **app password** (Google Account → Security → App passwords).
2. In `mysite/settings.py`, delete the `EMAIL_BACKEND = '...console...'` line and uncomment the Gmail block under it.
3. Before `runserver`, set the details in the terminal (Windows):
   ```
   set EMAIL_USER=yourname@gmail.com
   set EMAIL_PASSWORD=your-16-letter-app-password
   ```

## How the code works

| File | What it does |
|---|---|
| `core/models.py` | `Post` (now linked to its author) and `EmailVerification`, which stores whether the email is verified plus a **hashed** OTP code, when it was sent and how many wrong guesses were made |
| `core/forms.py` | `RegisterForm` (requires a unique email), `LoginForm`, `OTPForm`, `PostForm` |
| `core/emails.py` | `send_otp(user)` makes a new code and emails it |
| `core/backends.py` | Lets people log in with username **or** email |
| `core/views.py` | `register`, `LoginView`, `verify_email`, `resend_otp`, `dashboard`, `home` |
| `core/urls.py` | URLs for every page |
| `core/templates/core/` | `base.html` (layout and nav), `home.html`, `register.html`, `login.html`, `verify_email.html`, `dashboard.html` |
| `core/static/core/style.css` | All the styling |
| `core/tests.py` | 13 tests covering the whole flow. Run them with `python manage.py test core` |

### The flow

```
Register ──► code emailed ──► Verify page ──► correct code ──► logged in ──► Dashboard
                                   │
Log in (not verified yet) ─────────┘  (a fresh code is sent)
```

### OTP rules (change them at the bottom of `settings.py`)

- Codes expire after **10 minutes** (`OTP_EXPIRY_MINUTES`).
- **5 wrong attempts** lock the code, and the user must request a new one (`OTP_MAX_ATTEMPTS`).
- A new code can be requested once every **60 seconds** (`OTP_RESEND_SECONDS`).
- Codes are stored hashed, like passwords, so someone who can read the database still can't see them.
- Superusers made with `createsuperuser` skip verification, so the admin always works.

## Fixes to the code from class

- `def _str_` → `def __str__` (two underscores on each side).
- `views.py` was missing `from django.shortcuts import render`.
- `'core'` added to `INSTALLED_APPS` in `settings.py`.
- Logout is a **POST** form button, because newer Django versions no longer allow logging out with a plain link.

## Using MySQL instead of SQLite (optional)

The project uses SQLite by default, so it works with no setup. If your lecturer wants MySQL:

1. `pip install pymysql`
2. At the top of `mysite/__init__.py`, add:
   ```python
   import pymysql
   pymysql.install_as_MySQLdb()
   ```
3. Replace `DATABASES` in `settings.py` with:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'mysite_db',
           'USER': 'root',
           'PASSWORD': 'your-mysql-password',
           'HOST': 'localhost',
           'PORT': '3306',
       }
   }
   ```
4. Create the `mysite_db` database in MySQL, then run `python manage.py migrate`.
