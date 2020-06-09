import os

from flask import Flask, render_template, session, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests, json  # for goodreads API

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Default Route: Homepagae
@app.route("/", methods=["POST","GET"])
def index():
        if "username" in session:
            userprofile =db.execute("SELECT * FROM users WHERE username= :ida LIMIT 1", {"ida":session["username"]}).fetchone()
            reviews = db.execute("SELECT title, rating, review FROM reviews JOIN books ON reviews.bookid = books.id WHERE userid=:uid", {"uid":session["id"]}).fetchall()
            return render_template("search.html", session=session, userprofile = userprofile, reviews = reviews)
        else:
            return render_template("index.html")

    
# Signing Up to the users table

@app.route("/signup", methods=["POST","GET"])
def signup():
    if request.method == "POST":
        fname = request.form.get("fname")    
        lname = request.form.get("lname")    
        username = request.form.get("username")    
        password = request.form.get("password")    
        userp =db.execute("SELECT * FROM users WHERE username= :username LIMIT 1", {"username":username}).fetchone()
        if userp:
            return render_template("index.html", errormessage= "Username Already exists please try again")

        db.execute("INSERT INTO users (fname,lname,username,password) VALUES (:fname, :lname, :username, :password)",{"fname":fname, "lname":lname, "username":username, "password":password})
        db.commit()
        session["username"] = username
        userprofile =db.execute("SELECT * FROM users WHERE username= :ida LIMIT 1", {"ida":session["username"]}).fetchone()
        session["id"] = userprofile["id"]
        reviews = db.execute("SELECT title, rating, review FROM reviews JOIN books ON reviews.bookid = books.id WHERE userid=:uid", {"uid":session["id"]}).fetchall()
        return render_template("search.html",session=session, userprofile= userprofile, reviews= reviews)        
    else:
        return render_template("signup.html")

#Home Route
@app.route("/home")
def home():
    if "username" in session:
        userprofile =db.execute("SELECT * FROM users WHERE username= :ida LIMIT 1", {"ida":session["username"]}).fetchone()
        reviews = db.execute("SELECT title, rating, review FROM reviews JOIN books ON reviews.bookid = books.id WHERE userid=:uid", {"uid":session["id"]}).fetchall()
        return render_template("search.html",session=session, userprofile= userprofile, reviews= reviews)        
    else:
        return render_template("index.html")

# Logging In to the website
@app.route("/login", methods=["POST"])
def login():
    """Accepting and checking if Login Information is accurate """

    username = request.form.get("username")
    if not username: 
        return render_template("index.html",errormessage="Where is Username")
    
    password = request.form.get("password") 
    if not password: 
        return render_template("index.html",errormessage="Where is Password")

    userprofile =db.execute("SELECT * FROM users WHERE username= :ida LIMIT 1", {"ida":username}).fetchone()
    db.commit()
    if userprofile is None:
        return render_template("index.html",errormessage="User Doesnot Exists, Please try again")
    

    if userprofile["password"] != password:
        return render_template("index.html",errormessage="password doesnot match")

    session["username"] = username
    session["id"] = userprofile["id"]
    reviews = db.execute("SELECT title, rating, review FROM reviews JOIN books ON reviews.bookid = books.id WHERE userid=:uid", {"uid":session["id"]}).fetchall()
    return render_template("search.html",session=session,sucessmessage= f"You are now logged in as {username}", userprofile= userprofile, reviews= reviews)        
   
        

#Logging Out of the Website
@app.route("/logout", methods=["POST","GET"])
def logout():
    if "username" in session:
        del session["username"]
        del session["id"]
    return render_template("index.html",errormessage="You have Sucessfully Logged Out")

#Searching for books
@app.route("/search", methods=["POST","GET"])
def search():
    searchvalue = request.form.get("searchvalue")
    stype = request.form.get("stype")
    searchvalue = str(f"%{searchvalue}%")
    if stype == "title":
        searchresults = db.execute("SELECT * FROM books WHERE UPPER(title) LIKE :searchvalue ", {"searchvalue": searchvalue.upper() }).fetchall()
    if stype == "author":
        searchresults = db.execute("SELECT * FROM books WHERE UPPER(author) LIKE :searchvalue ", {"searchvalue": searchvalue.upper() }).fetchall()
    if stype == "isbn":
        searchresults = db.execute("SELECT * FROM books WHERE UPPER(isbn) LIKE :searchvalue ", {"searchvalue": searchvalue.upper() }).fetchall()
    if stype == "date":
        searchresults = db.execute("SELECT * FROM books WHERE UPPER(date) LIKE :searchvalue ", {"searchvalue": searchvalue.upper() }).fetchall()
    
    db.commit()
    if searchresults:
        return render_template("result.html", res = searchresults)
    else:
        return render_template("index.html", errormessage="Book Not found")

#The books page
@app.route("/book/<int:bookid>")
def bookp(bookid):
    if "username" in session:
        book = db.execute("SELECT * FROM books WHERE id= :bookid",{"bookid": bookid}).fetchone()
        isbn = book.isbn
        grev = requests.get("https://www.goodreads.com/book/review_counts.json", params= {"key": "DgJ6s0fQxCDMi6pv2ZLQA", "isbns":isbn, "format": "json" }).json()
        myrev = db.execute("SELECT * FROM reviews WHERE userid = :uid AND bookid = :bid", { "bid": bookid, "uid": session["id"]}).fetchall()
        allrev = db.execute("SELECT review, rating, fname, lname FROM reviews JOIN users ON reviews.userid = users.id WHERE bookid = :bid", {"bid": bookid}).fetchall()
        #Calculating Average Rating 
        avgrats = db.execute("SELECT ROUND(AVG(rating)) FROM reviews WHERE bookid = :bid", {"bid": bookid}).fetchone()
        avgrat = dict(avgrats)
        return render_template("book.html", book=book, grev= grev, myrev=myrev , allrev= allrev, avgrat= avgrat["round"])
    
    else:
        return render_template("index.html", errormessage= "Please Log In")

    

# reviews
@app.route("/reviews", methods=["POST"])
def reviews():
    review = request.form.get("review")
    bid = request.form.get("id")
    rating = request.form.get("rating")
    myrev = db.execute("SELECT * FROM reviews WHERE userid = :uid", {"uid": session["id"]}).fetchone()
    if myrev:
        db.execute("UPDATE reviews SET review = :review, rating = :rating WHERE bookid = :bid AND userid = :uid",{ "review": review, "rating": rating ,"bid": bid, "uid": session["id"]})
        db.commit()
        return bookp(bid)
    else:
        db.execute("INSERT INTO reviews (bookid, userid, review, rating) Values (:bid, :uid, :review, :rating) ",{ "review": review, "rating": rating,"uid":session["id"], "bid": bid})
        db.commit()
        return bookp(bid)

#Our own API
@app.route("/api/<isbn>", methods = ["GET"])
def api(isbn):
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn ", {"isbn": isbn }).fetchone()
    if books:
        book = dict(books)
        revdats = db.execute("SELECT COUNT(review), ROUND(AVG(rating)) FROM reviews WHERE bookid = :bid", {"bid": book["id"]}).fetchone()
        revdat = dict(revdats)
        if revdat['round']:
            book["review_count"] = revdat['count']
            book["average_score"] = int(revdat['round'])
        else:
            book["review_count"] = 0
            book["average_score"] = 0
        
        grev = requests.get("https://www.goodreads.com/book/review_counts.json", params= {"key": "DgJ6s0fQxCDMi6pv2ZLQA", "isbns":isbn, "format": "json" }).json()
        book["GoodReads_Review_Count"] = grev["books"][0]["reviews_count"]
        book["GoodReads_Average_Ratings"] = grev["books"][0]["average_rating"]
        book["year"] = book["date"]
        return json.dumps(book)
    else:
        return ("ERROR 404")
