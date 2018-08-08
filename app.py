import json
import os
import time
from datetime import timedelta, datetime

from flask import Flask, render_template, redirect, request, escape, jsonify, flash, current_app
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
import stripe

# Upon this import, backend/setup/__init__.py is run
from backend.stripe import app, db, User, Stripe, login_manager, csrf, stripe_api

# Import all routes from stripe.py
app.register_blueprint(stripe_api)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route("/")
def home():
    variables = dict(is_authenticated=current_user.is_authenticated)
    return render_template('index.html', **variables)

@app.route("/signup", methods=["POST"])
def signup():
    try:
        # Get data from AJAX request
        data = request.get_json(force=True)
        email = data['email']
        password = data['password']

        # Hash the password (store only the hash)
        pw_hash = generate_password_hash(password, 10)

        # Save user in database
        new_user = User(email=email, password_hash=pw_hash)
        db.session.add(new_user)
        db.session.commit()

        return json.dumps({'message':'/login_page'}), 200
    except exc.IntegrityError as ex:
        db.session.rollback()
        return json.dumps({'message':'Email already in use, tried logging in?'}), 403
    except Exception as ex:
        return json.dumps({'message':'Something went wrong'}), 401
    
@app.route("/login_page")
def login_page():
    if current_user.is_authenticated:
        return redirect('/dashboard', code=302)
    return render_template('login_page.html')

@app.route("/login", methods=["POST"])
def login():
    try:
        # Get data from AJAX request
        data = request.get_json(force=True)
        email = data['email']
        password = data['password']

        # Find user
        user = User.query.filter_by(email=email).first()

        # If user exists, check if email and password matches
        if user != None:
            check_pw = check_password_hash(user.password_hash, password)
            if user.email == email and check_pw:
                login_user(user, remember=True)
                return json.dumps({'message':'/dashboard'}), 200
            else:
                return json.dumps({'message':'User data incorrect'}), 401
        else:
            return json.dumps({'message':'Email not registered'}), 401
    except Exception as ex:
        return json.dumps({'message':'Unknown error, we apologize'}), 500
@app.route("/dashboard")
@login_required
def dashboard():
    trial_period = timedelta(days=app.config['TRIAL_LENGTH_DAYS'])
    timestamp = time.time()
    show_reactivate = None
    sub_active = None
    sub_cancelled_at = None

    stripe_obj = Stripe.query.filter_by(user_id=current_user.id).first()

    if stripe_obj != None:
        if stripe_obj.subscription_cancelled_at != None and timestamp < stripe_obj.subscription_cancelled_at:
            show_reactivate = True
        sub_active = stripe_obj.subscription_active
        sub_cancelled_at = stripe_obj.subscription_cancelled_at
        
        if sub_cancelled_at != None:
            sub_cancelled_at =  datetime.utcfromtimestamp(sub_cancelled_at).strftime('%Y-%m-%d %H:%M:%S')

    variables = dict(email=current_user.email,
                     expire_date=current_user.created_date + trial_period,
                     user_is_paying=sub_active,
                     show_reactivate=show_reactivate,
                     subscription_cancelled_at=sub_cancelled_at)
    
    return render_template('dashboard.html', **variables)

@app.route("/billing")
@login_required
def billing():
    timestamp = time.time()
    show_reactivate = None
    sub_active = None

    stripe_obj = Stripe.query.filter_by(user_id=current_user.id).first()

    if stripe_obj != None:
        if stripe_obj.subscription_cancelled_at != None and timestamp < stripe_obj.subscription_cancelled_at:
            show_reactivate = True
        sub_active = stripe_obj.subscription_active

    variables = dict(subscription_active=sub_active,
                     email=current_user.email,
                     show_reactivate=show_reactivate)
    
    return render_template('billing.html', **variables)

@app.route("/tos")
def terms_of_service():
    variables = dict(is_authenticated=current_user.is_authenticated)
    return render_template('terms_of_service.html', **variables)

@app.route("/logout")
def logout():
    current_user.is_authenticated = False
    logout_user()
    return redirect('/', code=302)
    
@app.errorhandler(401)
def not_logged_in(e):
    variables = dict(message='Please login first')
    
    return render_template('login_page.html', **variables)

@app.errorhandler(404)
def not_found(e):
    variables = dict(is_authenticated=current_user.is_authenticated,
                     message = '404 Page Not Found',
                     stacktrace = str(e))
    
    return render_template('error.html', **variables)

if __name__ == '__main__':
    app.run(host='0.0.0.0')