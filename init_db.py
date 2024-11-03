from app import app, db
from models import User, MessageTemplate

def create_admin():
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
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

        # Create sample message templates
        sample_templates = [
            {
                'name': 'Business Hours',
                'description': 'Response for business hours inquiry',
                'trigger_keywords': 'hours,open,business hours,operating hours',
                'response_template': 'Our business hours are Monday-Friday 9 AM to 5 PM EST.'
            },
            {
                'name': 'General Support',
                'description': 'Generic support response',
                'trigger_keywords': 'help,support,assistance',
                'response_template': 'Thank you for reaching out. Our support team will assist you shortly. For immediate assistance, please provide specific details about your issue.'
            },
            {
                'name': 'Service Pricing',
                'description': 'Information about pricing',
                'trigger_keywords': 'price,cost,pricing,rates',
                'response_template': 'Our service pricing starts at $99/month. For detailed pricing information, please visit our website or contact our sales team.'
            }
        ]

        # Add sample templates
        for template_data in sample_templates:
            template = MessageTemplate(**template_data)
            db.session.add(template)
        
        db.session.commit()
        print("Sample templates created successfully")

if __name__ == "__main__":
    create_admin()
