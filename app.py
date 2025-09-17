from flask import Flask, render_template, request, redirect, flash
from ebaysdk.trading import Connection as Trading
from datetime import datetime
from dotenv import load_dotenv  
import os
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for flash messages

load_dotenv()

# Your eBay API keys (sandbox or production)
APP_ID = os.getenv('APP_ID')
DEV_ID = os.getenv('DEV_ID')
CERT_ID = os.getenv('CERT_ID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')   # user token (not just app keys)

# Gmail STMP variables
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Upload configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- eBay Listings Route ---
@app.route("/")
def index():
    page = int(request.args.get("page", 1))
    items_per_page = 20

    api = Trading(
        config_file=None,
        appid=APP_ID,
        devid=DEV_ID,
        certid=CERT_ID,
        token=AUTH_TOKEN,
        siteid="0",
        warnings=True
    )

    response = api.execute("GetMyeBaySelling", {
        "ActiveList": {
            "Pagination": {
                "EntriesPerPage": items_per_page,
                "PageNumber": page
            }
        }
    })

    active_items = response.dict().get("ActiveList", {}).get("ItemArray", {}).get("Item", [])

    listings = []
    for item in active_items:
        listings.append({
            "title": item.get("Title"),
            "price": item.get("SellingStatus", {}).get("CurrentPrice", {}).get("value"),
            "currency": item.get("SellingStatus", {}).get("CurrentPrice", {}).get("_currencyID"),
            "url": item.get("ListingDetails", {}).get("ViewItemURL"),
            "image": item.get("PictureDetails", {}).get("GalleryURL"),
        })

    return render_template(
        "index.html",
        listings=listings,
        page=page,
        current_year=datetime.now().year
    )

# --- Selling Form Route ---
@app.route("/selling", methods=["GET", "POST"])
def selling():
    
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        files = request.files.getlist("images")

        if len(files) > 20:
            flash("You can upload up to 20 images only.")
            return redirect("/selling")

        saved_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                saved_files.append(filepath)

        # Send email
        msg = EmailMessage()
        msg["Subject"] = "New Selling Submission"
        msg["From"] = "leonardw@gmail.com"
        msg["To"] = "leonardw@gmail.com"
        msg.set_content(f"Name: {name}\nEmail: {email}\nPhone: {phone}")

        for path in saved_files:
            with open(path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(path)
            msg.add_attachment(file_data, maintype="image", subtype="jpeg", filename=file_name)

        try:
            # trying to send using gmail smtp server
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
            flash("Submission sent successfully!")
        except Exception as e:
            flash(f"Error sending email: {e}")

        # Clean up uploaded files
        for path in saved_files:
            os.remove(path)

        return redirect("/selling")

    return render_template("selling.html", current_year=datetime.now().year)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
