from pathlib import Path
from datetime import datetime, timedelta
from secrets import token_urlsafe
import csv, io
import qrcode
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from config import Config
from .models import db, User, Category, CustomField, CustomFieldValue, Identification, ScanLog

login_manager = LoginManager()
login_manager.login_view = 'login'
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    Path(app.config['QR_DIR']).mkdir(parents=True, exist_ok=True)
    db.init_app(app); login_manager.init_app(app); csrf.init_app(app)
    with app.app_context(): db.create_all()

    @login_manager.user_loader
    def load_user(user_id): return db.session.get(User, int(user_id))

    @app.context_processor
    def globals(): return {'now': datetime.utcnow(), 'active_page': request.endpoint or ''}

    @app.route('/login', methods=['GET','POST'])
    def login():
        if current_user.is_authenticated: return redirect(url_for('dashboard'))
        if request.method == 'POST':
            user = User.query.filter((User.username == request.form.get('identity')) | (User.email == request.form.get('identity'))).first()
            if user and user.status == 'Active' and user.check_password(request.form.get('password','')):
                user.last_login=datetime.utcnow(); db.session.commit(); login_user(user, remember=bool(request.form.get('remember'))); return redirect(url_for('dashboard'))
            flash('The credentials were not recognized.', 'error')
        return render_template('login.html')

    @app.get('/logout')
    @login_required
    def logout(): logout_user(); return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def dashboard():
        today=datetime.utcnow().date(); records=Identification.query.order_by(Identification.created_at.desc()).all()
        return render_template('dashboard.html', records=records[:6], total=len(records), active=sum(r.status=='Active' for r in records), inactive=sum(r.status != 'Active' for r in records), scans=ScanLog.query.count(), today=ScanLog.query.filter(ScanLog.scanned_at >= datetime.combine(today, datetime.min.time())).count())

    @app.route('/identifications')
    @login_required
    def identifications():
        query=Identification.query
        search=request.args.get('q','').strip(); status=request.args.get('status',''); category=request.args.get('category','')
        if search: query=query.filter((Identification.name.ilike(f'%{search}%')) | (Identification.public_id.ilike(f'%{search}%')))
        if status: query=query.filter_by(status=status)
        if category: query=query.filter_by(category=category)
        return render_template('identifications.html', records=query.order_by(Identification.created_at.desc()).all(), categories=Category.query.filter_by(active=True).all())

    @app.route('/identifications/new', methods=['GET','POST'])
    @login_required
    def identification_new():
        fields=CustomField.query.filter_by(active=True).all()
        if request.method=='POST':
            record=Identification(public_id=f'ID-{token_urlsafe(5).upper()}', qr_token=token_urlsafe(32), name=request.form.get('name','').strip(), category=request.form.get('category','Other'), email=request.form.get('email'), phone=request.form.get('phone'), address=request.form.get('address'), organization=request.form.get('organization'), department=request.form.get('department'), designation=request.form.get('designation'), status=request.form.get('status','Active'), notes=request.form.get('notes'))
            if not record.name: flash('Name is required.', 'error'); return render_template('form.html', fields=fields, record=record)
            db.session.add(record); db.session.flush()
            for field in fields:
                value=request.form.get(f'custom_{field.id}')
                if value: db.session.add(CustomFieldValue(identification_id=record.id,custom_field_id=field.id,value=value))
            db.session.commit(); generate_qr(record, app); flash('Identification created and QR generated.', 'success'); return redirect(url_for('identification_view', record_id=record.id))
        return render_template('form.html', fields=fields, record=None)

    @app.route('/identifications/<int:record_id>/edit', methods=['GET','POST'])
    @login_required
    def identification_edit(record_id):
        record=Identification.query.get_or_404(record_id); fields=CustomField.query.filter_by(active=True).all()
        if request.method=='POST':
            for key in ['name','category','email','phone','address','organization','department','designation','status','notes']: setattr(record,key,request.form.get(key))
            for field in fields:
                value=CustomFieldValue.query.filter_by(identification_id=record.id,custom_field_id=field.id).first()
                new=request.form.get(f'custom_{field.id}')
                if value: value.value=new
                elif new: db.session.add(CustomFieldValue(identification_id=record.id,custom_field_id=field.id,value=new))
            db.session.commit(); flash('Record updated.', 'success'); return redirect(url_for('identification_view',record_id=record.id))
        return render_template('form.html', fields=fields, record=record)

    @app.get('/identifications/<int:record_id>')
    @login_required
    def identification_view(record_id): return render_template('view.html', record=Identification.query.get_or_404(record_id))

    @app.get('/identifications/<int:record_id>/qr')
    @login_required
    def qr_view(record_id):
        record=Identification.query.get_or_404(record_id); generate_qr(record,app); return render_template('qr.html',record=record)

    @app.get('/qr/<token>.png')
    def qr_png(token):
        record=Identification.query.filter_by(qr_token=token).first_or_404(); generate_qr(record,app); return send_file(Path(app.config['QR_DIR']) / f'{record.public_id}.png', mimetype='image/png', as_attachment=True, download_name=f'{record.public_id}.png')

    @app.get('/identify/<token>')
    def identify(token):
        record=Identification.query.filter_by(qr_token=token).first(); status='Verified'
        if not record: return render_template('public.html',record=None,status='Unknown'),404
        if record.status != 'Active': return render_template('public.html',record=record,status='Inactive'),410
        record.last_scanned_at=datetime.utcnow(); db.session.add(ScanLog(identification_id=record.id,qr_token=token,ip_address=request.remote_addr,user_agent=request.user_agent.string)); db.session.commit()
        return render_template('public.html',record=record,status=status)

    @app.route('/fields', methods=['GET','POST'])
    @login_required
    def fields():
        if request.method=='POST':
            field=CustomField(name=request.form.get('name','').lower().replace(' ','_'),label=request.form.get('label',''),field_type=request.form.get('field_type','text'),options=request.form.get('options')); db.session.add(field); db.session.commit(); flash('Custom field added.', 'success'); return redirect(url_for('fields'))
        return render_template('fields.html',fields=CustomField.query.order_by(CustomField.created_at.desc()).all())

    @app.get('/scans')
    @login_required
    def scans(): return render_template('scans.html', logs=ScanLog.query.order_by(ScanLog.scanned_at.desc()).all())

    @app.get('/scanner')
    @login_required
    def scanner(): return render_template('scanner.html')

    @app.get('/reports')
    @login_required
    def reports(): return render_template('reports.html', records=Identification.query.all(), logs=ScanLog.query.all())

    @app.get('/api/dashboard/stats')
    @login_required
    def api_stats(): return jsonify(total=Identification.query.count(), active=Identification.query.filter_by(status='Active').count(), scans=ScanLog.query.count(), categories=[{'name':c.name,'count':Identification.query.filter_by(category=c.name).count()} for c in Category.query.all()])

    @app.get('/api/identifications')
    @login_required
    def api_records(): return jsonify([record_json(r) for r in Identification.query.all()])

    @app.get('/api/identify/<token>')
    def api_identify(token):
        record=Identification.query.filter_by(qr_token=token).first()
        if not record or record.status != 'Active': return jsonify(error='QR Code Inactive' if record else 'Unknown QR'),404
        return jsonify(record_json(record, public=True))

    @app.get('/export/scans.csv')
    @login_required
    def export_scans():
        output=io.StringIO(); writer=csv.writer(output); writer.writerow(['Scan ID','QR ID','Entity','Date','IP','Status'])
        for log in ScanLog.query.order_by(ScanLog.scanned_at.desc()): writer.writerow([log.id,log.identification.public_id if log.identification else '-',log.identification.name if log.identification else '-',log.scanned_at,log.ip_address,log.status])
        return send_file(io.BytesIO(output.getvalue().encode()),mimetype='text/csv',as_attachment=True,download_name='scan-history.csv')

    @app.errorhandler(403)
    def forbidden(e): return render_template('error.html',code=403,message='You do not have permission to access this area.'),403
    @app.errorhandler(404)
    def missing(e): return render_template('error.html',code=404,message='That page could not be found.'),404
    return app

def generate_qr(record, app):
    image=qrcode.make(url_for('identify',token=record.qr_token,_external=True)); image.save(Path(app.config['QR_DIR']) / f'{record.public_id}.png')

def record_json(r, public=False):
    data={'id':r.id,'public_id':r.public_id,'name':r.name,'category':r.category,'status':r.status,'organization':r.organization}
    if not public: data.update(email=r.email,phone=r.phone,qr_token=r.qr_token,created_at=r.created_at.isoformat())
    return data
