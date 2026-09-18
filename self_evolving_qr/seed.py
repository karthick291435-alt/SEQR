from app import create_app
from app.models import db, User, Category, CustomField, Identification
from secrets import token_urlsafe

app = create_app()
with app.app_context():
    db.drop_all(); db.create_all()
    users = [('Aarav Mehta','admin','admin@demo.local','Super Admin','Admin@123'),('Maya Joseph','manager','maya@demo.local','Admin','Admin@123'),('Leo Martin','operator','leo@demo.local','Operator','Admin@123')]
    for name, username, email, role, password in users:
        user=User(name=name, username=username, email=email, role=role); user.set_password(password); db.session.add(user)
    for name in ['Student','Employee','Customer','Product','Visitor','Member']:
        db.session.add(Category(name=name, description=f'{name} identification records'))
    fields=[('blood_group','Blood Group','dropdown','A+,B+,AB+,O+,O-'),('employee_id','Employee ID','text',''),('course','Course','text',''),('emergency_contact','Emergency Contact','phone',''),('membership_type','Membership Type','dropdown','Standard,Premium,Partner')]
    for name,label,kind,options in fields: db.session.add(CustomField(name=name,label=label,field_type=kind,options=options,required=False))
    names=['Nila Raman','Arjun Das','Sofia Lee','Vikram Shah','Mira Patel','Noah Wilson','Anika Roy','Ethan Cole','Sara Khan','Dev Iyer','Isha Menon','Ryan Bell','Tara Singh','Kian Joseph','Lena Park']
    cats=['Student','Employee','Customer','Product','Visitor']
    for i,name in enumerate(names):
        db.session.add(Identification(public_id=f'ID-{1001+i}',qr_token=token_urlsafe(32),name=name,category=cats[i%5],email=f'{name.lower().replace(" ",".")}@example.test',organization='Northstar Collective',department='Operations',designation='Member',status='Revoked' if i==14 else ('Inactive' if i in [4,9] else 'Active')))
    db.session.commit()
    print('Seeded database. Login: admin / Admin@123')
