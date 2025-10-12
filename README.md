# 📝 Flask Diary App

A secure, feature-rich offline diary built with Python Flask. Perfect for developers, students, and writers who want a powerful journaling tool that keeps data private and local.

---

## 🚀 Features

- 🕒 Timestamped diary entries with full metadata (mood, weather, location, tags)
- 🔍 Advanced search functionality with date filters
- 📊 Statistics dashboard with insights and analytics
- 🏷️ Categories and tags for organization
- 📤 Export entries (JSON/TXT format)
- 🔐 Secure authentication with password hashing
- 🛡️ CSRF protection and security best practices
- ✨ Clean, responsive UI with dark mode support
- 🔐 Fully offline — your data stays on your device
- 🛠 Easy to customize (Python + Flask)

---

## 🗂 What's Included

- ✅ Full Flask source code with security enhancements
- 📘 Setup instructions
- 🖼 Screenshots of the UI
- 📄 Configuration management
- 🔒 Environment variable template

---

## 🧰 Requirements

- Python 3.8+
- Dependencies in `requirements.txt`

## 📦 Installation

1. **Clone or download the repository**

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables** (optional):
```bash
# Copy the example file
copy .env.example .env  # Windows
# or
cp .env.example .env  # Linux/Mac

# Edit .env and set your SECRET_KEY
```

5. **Run the application**:
```bash
python app.py
```

6. **Open your browser**:
```
http://127.0.0.1:5000/
```

---

## 🔒 Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **CSRF Protection**: Flask-WTF CSRF tokens on all forms
- **Session Security**: Secure session cookies with HTTPOnly flag
- **Database Indexes**: Optimized queries for better performance
- **Input Validation**: Content length and format validation
- **Error Handling**: Comprehensive error logging and user feedback

---

## 🎯 Usage

1. **Register** a new account
2. **Login** with your credentials
3. **Write** diary entries with rich metadata
4. **Search** and filter your entries
5. **View statistics** about your journaling habits
6. **Export** your data anytime

---

## 🔧 Configuration

The app uses a configuration system (`config.py`) with different environments:
- **Development**: Debug mode enabled
- **Production**: Security hardened, HTTPS required
- **Testing**: In-memory database

---

## 📝 License

This project is open source and available for personal use.