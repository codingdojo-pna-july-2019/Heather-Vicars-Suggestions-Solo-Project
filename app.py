from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, Table, MetaData, select
from sqlalchemy.sql import func
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from  datetime import datetime, timedelta
from flask_marshmallow import Marshmallow

import re
import json

			
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///suggestions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

app.secret_key = "b_5#c]/2Lyz\n\xeF4Q8"
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
INVALID_PASSWORD_REGEX = re.compile(r'^([^0-9]*|[^A-Z]*|[^a-z]*|[^!@#$%^&*()_+=]*)$')
bcrypt = Bcrypt(app) 

likes_table = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('suggestion_id', db.Integer, db.ForeignKey('suggestions.id'), primary_key=True))

class Users(db.Model):
    __tablename__="users"
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(45))
    alias = db.Column(db.String(45))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    likes_by_user = db.relationship('Suggestions', secondary=likes_table)
   
    def user_is(self):
        return "{} {}".format(self.fname)

    @classmethod
    def validate_registration(cls, form):
        errors= []
        if len(form["fname"]) < 5:
            errors.append("Enter at least 5 characters for your name.")
        if len(form["alias"]) < 5:
            errors.append("Enter at least 5 characters for your alias.")    
        if not EMAIL_REGEX.match(form["email"]):
            errors.append("Enter a valid email address.")
        existing_alias = Users.query.filter_by(alias=form['alias']).first()
        if existing_alias:
            errors.append("This alias is already in use, please choose another.")
        existing_emails = Users.query.filter_by(email=form['email']).first()
        if existing_emails:
            errors.append("This email address is already in use.")
        if len(form["password"]) < 8:
            errors.append("Passwords must contain at least 8 characters.")
        if INVALID_PASSWORD_REGEX.match(form["password"]):
            errors.append("Password must have at least one lower case, one uppercase, one number, and one special character.")
        if form['password'] != form["confirm_password"]:
            errors.append("The password and password confirmation entered do not match.")
        return errors

    @classmethod
    def create(cls, form):
        usernew = cls(
            fname=form['fname'],
            alias=form['alias'],
            email=form['email'],
            password_hash=bcrypt.generate_password_hash(form['password'])
        )
        db.session.add(usernew)
        db.session.commit()

    @classmethod
    def login_validation(cls, form):
        user_info = Users.query.filter_by(email = form['email']).first()
        if user_info:   
            if bcrypt.check_password_hash(user_info.password_hash, form['password']):
                session['loggedin_user'] = {
                    "user_id": user_info.id,
                    "fname": user_info.fname,
                    "alias": user_info.alias,
                    "email": user_info.email
                }
                return (True)
        return (False)

    @classmethod
    def liking_suggestion(cls, form):
        suggestion_id = Suggestions.query.get(form['suggestion_id'])
        id_who_likes = Users.query.get(form['user_id'])
        id_who_likes.likes_by_user.append(suggestion_id)
        db.session.commit()

class UsersSchema(ma.Schema):
    class Meta:
        model = Users

class Suggestions(db.Model):
    __tablename__="suggestions"
    id = db.Column(db.Integer, primary_key=True)
    suggestion = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, server_default = func.now())
    updated_at = db.Column(db.DateTime, server_default = func.now(), onupdate = func.now())
    author = db.relationship("Users", backref="Suggestions")
    liked_suggestion = db.relationship("Users", secondary = likes_table)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    @classmethod
    def validate_suggestion(cls, form):
        errors= []
        if len(form["suggestion"]) < 2:
            errors.append("Please enter a suggestion between 1 and 1000 characters")
        if len(form["suggestion"]) > 1000:
            errors.append("Please enter a suggestion between 1 and 1000 characters")
        return errors

    @classmethod
    def create(cls, form):
        suggestionIsadded = cls(
            author_id=session['loggedin_user']['user_id'],
            suggestion=form['suggestion'],
        )
        db.session.add(suggestionIsadded)
        db.session.commit()

    @classmethod
    def update_suggestion(cls, form):
        updated_suggestion_content = cls(
            suggestion = form['suggestion'],
            id = form['suggestion_id']
        )
        a_suggestion = Suggestions.query.get(updated_suggestion_content.id)
        a_suggestion.suggestion = updated_suggestion_content.suggestion
        db.session.commit()

class SuggestionsSchema(ma.Schema):
    class Meta:
        model = Suggestions

# conveniently, Flask has a jsonify function

# def one():
#     one_item = SomeModel.query.first()
#     some_schema = SomeModelSchema()
#     output = some_schema.dump(one_item).data
#     return jsonify({"some_item": output})
# def all():
#     items = SomeModel.query.all()
#     some_schema = SomeModelSchema(many=True) # this is different!
#     output = some_schema.dump(items).data
#     return jsonify({"some_item": output})

@app.route('/')
def index():
    return render_template("landing.html")

@app.route('/gotoregister')
def gotoregistration():
    return render_template("register.html")

@app.route('/register', methods=["POST"])
def registration():
    errors = Users.validate_registration(request.form)
    if errors:
        for error in errors:
            flash(error)
    else:
        Users.create(request.form)
        flash("Thank you, your registration is complete. Please go to login to login.")
    return redirect("/gotoregister")

@app.route('/gotologin')
def gotologin():
    return render_template("login.html")

@app.route('/login', methods=["POST"])
def login():
    userA = Users.login_validation(request.form)
    if userA:
        return redirect('/suggestions')
    else:
        flash("Your email address and password are incorrect.")
    return redirect('/gotologin')

@app.route('/suggestions', methods=["POST", "GET"])
def suggestions():
    if 'loggedin_user' not in session:
        return redirect('/')
    return render_template("suggestions.html")

@app.route('/new_suggestion', methods=["POST"])
def new_suggestion():
    print(request.form)
    errors = Suggestions.validate_suggestion(request.form)
    if errors:
        for error in errors:
            flash(error)
            return redirect('/suggestions')
    else:
        Suggestions.create(request.form)
    return redirect('/suggestions')

@app.route('/like', methods=["POST"])
def like():
    Users.liking_suggestion(request.form)
    return redirect('/suggestions')

@app.route('/edit/<suggestion_id>')
def edit_suggestion(suggestion_id):
    session['suggestion_id_editing'] = suggestion_id
    return redirect('/loadedit')

@app.route('/loadedit')
def loadedit():
    edit_suggestion = Suggestions.query.filter_by(id = session['suggestion_id_editing'])
    return render_template("edit.html", edit_suggestion = edit_suggestion)

@app.route('/repostsuggestion', methods=["POST"])
def repostsuggestion():
    errors = Suggestions.validate_suggestion(request.form)
    if errors:
        for error in errors:
            flash(error)
            return redirect('/suggestions')
    else:
        Suggestions.update_suggestion(request.form)
    return redirect('/suggestions')

@app.route('/showSuggestion_async/<user_id>', methods=["GET"])
def showSuggestion(user_id):
    sendback = db.session.query(Suggestions).order_by(desc(Suggestions.id)).all()
    sendback2 = db.session.query(Users).all()
    query_likes = db.session.query((likes_table.c.suggestion_id), func.count(likes_table.c.user_id)).group_by(likes_table.c.suggestion_id).all()
    likes_list = db.session.query((likes_table.c.suggestion_id), (likes_table.c.user_id)).order_by(desc(likes_table.c.suggestion_id)).all()

    list_of_all_Suggestion = []
    for t in sendback:
        list_of_all_Suggestion.append(t.id)

    Suggestion_with_likes = []
    for suggestion in query_likes:
        Suggestion_with_likes.append(suggestion[0])

    all_current_user_likes_suggestion_id = []
    for like in likes_list:
        if like[1] == session['loggedin_user']['user_id']:
            all_current_user_likes_suggestion_id.append(like[0])

    Suggestion_loggedin_user_hasnot_liked = []
    for i in list_of_all_Suggestion:
        likes = "False"
        for y in all_current_user_likes_suggestion_id:
            if i == y:
                likes = "True"
        if likes == "False":
            Suggestion_loggedin_user_hasnot_liked.append(i)
    return render_template("/partials/suggestionfeed.html", suggestionfeed = sendback, authors = sendback2, likes= query_likes, not_liked = Suggestion_loggedin_user_hasnot_liked)

@app.route('/suggestiondetails/<suggestion_id>', methods=["GET"]) #new page starts here
def suggestiondetails(suggestion_id):
    session['suggestion_id'] = suggestion_id
    return redirect('/seesuggestion')

@app.route('/seesuggestion')
def seesuggestion():
    suggestion_details = Suggestions.query.filter_by(id = session['suggestion_id'])
    author_details = Users.query.filter_by(id = suggestion_details[0].author_id)
    return render_template("suggestiondetails.html", suggestion_details = suggestion_details, author_details = author_details)

@app.route('/showLikes_async', methods=["GET"])
def showLikes():
    suggestion_id_liked = session['suggestion_id']
    user_likes_list = db.session.query(Users).join(likes_table).filter(suggestion_id_liked == likes_table.c.suggestion_id).all()
    user_info = []
    user_info.append(("test", "test"))
    if user_likes_list:
        for eachuser in user_likes_list:
            thisuser = (eachuser.alias, eachuser.fname)
            user_info.append(thisuser)
    return render_template("/partials/likestable.html", likes_list = user_info)

@app.route('/userprofile/<alias>')
def userprofile(alias):
    users_profile = db.session.query(Users).filter(Users.alias == alias).first()
    numlikes = db.session.query(likes_table.c.suggestion_id).filter(users_profile.id == likes_table.c.user_id).all()
    count = 0
    for like in numlikes:
        count = count+1
    numlikesis = count
    numposts = db.session.query(Suggestions).filter(users_profile.id == Suggestions.author_id)
    count2 = 0
    for post in numposts:
        count2 = count2+1
    numpostsis = count2
    return render_template("userprofile.html", users_profile = users_profile, numposts = numpostsis, numlikes = numlikesis)



@app.route('/delete', methods=['POST'])
def deletesuggestion():
    id_to_delete = {
        "id": request.form["suggestion_id"]
    }
    suggestion_to_delete = Suggestions.query.get(id_to_delete['id'])
    db.session.delete(suggestion_to_delete)
    db.session.commit()
    return redirect('/suggestions')

@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)