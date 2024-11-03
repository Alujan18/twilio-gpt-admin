from app import app, db
from models import User

def create_admin():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin user exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin')  # Default password, should be changed
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
        else:
            print("Admin user already exists")

if __name__ == "__main__":
    create_admin()
