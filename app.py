import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    uid = session["user_id"]
    allStocks = db.execute("SELECT * FROM portfolio WHERE id=:id", id=uid)

    # Get current price and total value for each stock
    for s in allStocks:
        symbol = s["stock"]
        info = lookup(symbol)
        price = info["price"]
        s["price"] = round(price,2)
        s["total"] = round(s["shares"] * price, 2)

    # Get cash balance and the grand total
    rows = db.execute("SELECT cash FROM users WHERE id = :id", id=uid)
    cash = round(rows[0]["cash"], 2)
    grandTotal = cash
    for s in allStocks:
        grandTotal += s["total"]
    grandTotal = round(grandTotal, 2)

    return render_template("index.html", stocks=allStocks, cash=cash, grandTotal=grandTotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        numShares = int(request.form.get("shares"))
        uid = session["user_id"]

        # Check for valid user inputs
        if not symbol or not numShares:
            return apology("All fields are requried", 403)
        if numShares <= 0:
            return apology("Number of shares must be a positive integer!", 403)
        stockInfo = lookup(symbol)
        if not stockInfo:
            return apology("Cannot find stock symbol", 403)

        price = stockInfo["price"]
        totalCost = price * numShares
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=uid)
        cash = rows[0]["cash"]
        cashLeft = cash - totalCost

        # Check if the user can afford the stock that s/he wants to buy,
        # if yes, update db for this user
        if cashLeft < 0:
            return apology("Not enough cash", 403)

        # Update transaction history
        db.execute("INSERT INTO transactions (id, stock, price, shares) " +\
                "VALUES (:id, :stock, :price, :shares)", id=uid,
                stock=symbol, price=price, shares=numShares)

        # Update user's profile
        db.execute("UPDATE users SET cash=:cashleft WHERE id=:id",\
                cashleft=cashLeft, id=uid)
        thisStock = db.execute("SELECT stock FROM portfolio WHERE stock=:stock", stock=symbol)
        if not thisStock:
            db.execute("INSERT INTO portfolio (id, stock, shares)\
                VALUES(:id, :stock, :shares)", id=uid, stock=symbol, shares=numShares)
        else:
            db.execute("UPDATE portfolio SET shares=shares+:shares " +\
                    "WHERE id=:id AND stock=:stock", shares=numShares, id=uid, stock=symbol)

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    uid = session["user_id"]
    transactions = db.execute("SELECT * FROM transactions WHERE id=:id", id=uid)
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Please enter a stock symbol!", 403)

        stockInfo = lookup(symbol)
        if not stockInfo:
            return apology("Cannot find stock symbol", 403)

        return render_template("quoted.html", stockInfo=stockInfo)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        un = request.form.get("username")
        pw = request.form.get("password")
        cf_pw = request.form.get("confirmation")

        # Ensure not field is left blank
        if not un or not pw or not cf_pw:
            return apology("All fields are required", 403)

        # Ensure username is not used
        rows = db.execute("SELECT username FROM users WHERE username = :username", username=un)
        if len(rows) != 0:
            return apology("This username has been used", 403)

        # Ensure passwords match
        if pw != cf_pw:
            return apology("Passwords don't match", 403)

        # Hash password
        hashed = generate_password_hash(pw)

        # Insert user record into db and log them in
        id = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",\
                username=un, hash=hashed)
        session["user_id"] = id
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Get user's stocks
    uid = session["user_id"]
    stocks = db.execute("SELECT stock FROM portfolio WHERE id=:id", id=uid)

    if request.method == "GET":
        return render_template("sell.html", stocks=stocks)
    else:
        symbol = request.form.get("symbol")
        numShares = int(request.form.get("shares"))

        # Check for valid user inputs
        if not symbol or not numShares:
            return apology("All fields are requried", 403)
        if numShares <= 0:
            return apology("Number of shares must be a positive integer!", 403)
        stockInfo = lookup(symbol)
        if not stockInfo:
            return apology("Cannot find stock symbol", 403)

        selectedStock = db.execute("SELECT * FROM portfolio WHERE id=:id AND " +\
                "stock=:stock", id=uid, stock=symbol)
        sharesAvailable = selectedStock[0]['shares']
        sharesLeft = sharesAvailable - numShares
        if sharesLeft < 0:
            return apology("Not enough shares to sell", 403)
        currentPrice = stockInfo['price']
        total = currentPrice * numShares

        # Update transaction history
        db.execute("INSERT INTO transactions (id, stock, price, shares) " +\
                "VALUES (:id, :stock, :price, -:shares)", id=uid,
                stock=symbol, price=currentPrice, shares=numShares)

        # Update user's portfolio
        if sharesLeft > 0:
            db.execute("UPDATE portfolio SET shares=:shares_left " +\
                    "WHERE id=:id AND stock=:stock", shares_left=sharesLeft, id=uid, stock=symbol)
        else:
            db.execute("DELETE FROM portfolio WHERE id=:id AND stock=:stock", id=uid, stock=symbol)

        # Update user's cash
        db.execute("UPDATE users SET cash=cash+:total WHERE id=:id", total=total, id=uid)

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
