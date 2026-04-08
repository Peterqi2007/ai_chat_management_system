AI Chat Management System
A secure, hierarchical chat content management system built with Django and Mezzanine, designed for categorizing, managing, and controlling access to LLM (Large Language Model) conversation records.
Features
Hierarchical structure: Category → Folder → Subfolder → Chat Entry
Privacy protection with password encryption for sensitive conversations
Independent data isolation for different users
Complete CRUD operations for chat records & folders
Customizable LLM parameters: temperature, top_p, max_tokens
Responsive UI with Bootstrap 5
Mezzanine CMS integration for page & content management
Secure password verification for private chats (per-access validation)
Tech Stack
Backend: Django 4.2+, Mezzanine 6.0+
Frontend: Bootstrap 5, Vanilla JavaScript
Database: SQLite (default), PostgreSQL/MySQL compatible
Security: Django Auth, CSRF protection, password hashing
LLM Support: Qwen, Minimax, and other mainstream LLMs
Installation & Setup
1. Clone the Repository
bash
运行
git clone https://github.com/Peterqi2007/ai_chat_management_system.git
cd ai_chat_management_system
2. Create Virtual Environment
bash
运行
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate
3. Install Dependencies
bash
运行
pip install -r requirements.txt
4. Environment Configuration
Create a .env file in the project root:
env
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# LLM API Keys (optional)
QWEN_API_KEY=your-qwen-api-key
MINIMAX_API_KEY=your-minimax-api-key
5. Database Migration
bash
运行
python manage.py makemigrations
python manage.py migrate
6. Create Superuser
bash
运行
python manage.py createsuperuser
7. Run Development Server
bash
运行
python manage.py runserver
Web: http://127.0.0.1:8000/
Admin: http://127.0.0.1:8000/admin/
Mezzanine CMS: http://127.0.0.1:8000/cms/
Usage
Create top-level Categories
Manage Folders & Subfolders under each category
Create & organize Chat Entries
Set passwords for private conversations
Configure LLM parameters for each chat
View, edit, delete records with permission control
Open Source License
This project is licensed under the MIT License – see the 
 file for details.
Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
