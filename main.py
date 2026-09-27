"""
main.py
-------
Entry point. Run this file (in PyCharm: right-click -> Run 'main') to launch
Universal POS. Initializes the database on first run, then shows the login
screen.
"""

from database import init_db
from login_window import LoginWindow

if __name__ == "__main__":
    init_db()
    app = LoginWindow()
    app.mainloop()
