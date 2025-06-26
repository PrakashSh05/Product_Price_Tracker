from flask import Flask, request, jsonify, redirect, url_for, flash, render_template
from flask_login import current_user, login_required
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import schedule
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash

# Headers for Amazon requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive'
}

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Configure MongoDB
app.config['MONGO_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/price_tracker')

# Initialize extensions
from extensions import mongo
mongo.init_app(app)

# Import blueprints
from auth import auth as auth_blueprint
from main import main as main_blueprint

# Register blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(main_blueprint)

# Add test email route
@app.route('/test-email', methods=['GET', 'POST'])
@login_required
def test_email():
    if request.method == 'POST':
        try:
            # Create a test product info
            test_product = {
                'title': 'Test Product - Price Drop Alert',
                'price': 999.99,
                'url': 'https://www.amazon.in',
                'image_url': 'https://via.placeholder.com/300?text=Test+Product'
            }
            
            # Get the threshold price from the form or use a default
            threshold_price = float(request.form.get('threshold_price', 1000))
            
            # Send test email
            send_price_alert(current_user.email, test_product, threshold_price)
            flash('Test email sent successfully! Check your inbox (and spam folder).', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            print(f"Error sending test email: {e}")
            flash('Failed to send test email. Please check the console for errors.', 'danger')
    
    # For GET request or if there was an error
    return render_template('test_email.html')

# Import login_manager from auth
from auth import login_manager

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.amazon.com/',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'TE': 'trailers'
}

# Initialize login manager
login_manager.init_app(app)

# Custom login_required decorator that handles both JSON and HTML responses
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Please log in to access this resource'}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function



# Database collections
db = mongo.db
products = db.products
price_history = db.price_history
users = db.users



# Email configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender': os.getenv('EMAIL_SENDER'),
    'password': os.getenv('EMAIL_PASSWORD')
}

class User:
    def __init__(self, user_data):
        self.id = user_data['email']  # Use email as the ID
        self.username = user_data.get('username', '')
        self.email = user_data['email']
        self.password_hash = user_data['password']
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.email

@login_manager.user_loader
def load_user(email):
    user_data = users.find_one({"email": email})
    if user_data:
        return User(user_data)
    return None

def get_amazon_product_info(url):
    import time
    from urllib.parse import urlparse, urljoin
    
    print(f"\n[get_amazon_product_info] Starting with URL: {url}")
    
    # Ensure URL is valid and from Amazon
    if not url:
        print("[get_amazon_product_info] Error: No URL provided")
        return None
        
    if 'amazon.' not in url:
        print(f"[get_amazon_product_info] Error: Not an Amazon URL: {url}")
        return None
    
    # Add random delay to avoid rate limiting
    delay = 2
    print(f"[get_amazon_product_info] Waiting {delay} seconds before request...")
    time.sleep(delay)
    
    # Ensure URL is absolute and uses HTTPS
    if url.startswith('//'):
        url = 'https:' + url
        print(f"[get_amazon_product_info] Fixed protocol-relative URL: {url}")
    elif url.startswith('/'):
        url = 'https://www.amazon.in' + url  # Default to amazon.in for relative URLs
        print(f"[get_amazon_product_info] Fixed relative URL: {url}")
    
    # Parse the URL to get domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Set referer based on domain
    headers = HEADERS.copy()
    domain_parts = domain.split('.')
    if len(domain_parts) >= 2:
        headers['Referer'] = f'https://www.{domain_parts[-2]}.{domain_parts[-1]}'
    else:
        headers['Referer'] = 'https://www.amazon.com/'
    
    print(f"[get_amazon_product_info] Using headers: {headers}")
    
    # Make the request with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Add some jitter to the delay between retries
            if attempt > 0:
                retry_delay = 2 ** attempt + random.uniform(0, 1)
                print(f"[get_amazon_product_info] Attempt {attempt + 1}/{max_retries}, waiting {retry_delay:.2f}s...")
                time.sleep(retry_delay)
            else:
                print(f"[get_amazon_product_info] Initial request attempt {attempt + 1}/{max_retries}")
            
            print(f"[get_amazon_product_info] Making request to: {url}")
            # Make the request without following redirects first
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
            print(f"[get_amazon_product_info] Response status: {response.status_code}")
            print(f"[get_amazon_product_info] Response headers: {response.headers}")
            
            # If we get a redirect, follow it
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get('Location', '')
                if redirect_url:
                    print(f"Following redirect to: {redirect_url}")
                    # Handle relative redirects
                    if redirect_url.startswith('/'):
                        domain = '.'.join(domain.split('.')[-2:])  # Get domain like 'amazon.in'
                        redirect_url = f'https://www.{domain}{redirect_url}'
                    response = requests.get(redirect_url, headers=headers, timeout=15)
            else:
                response.raise_for_status()
            
            # Check for CAPTCHA or bot detection
            response_text = response.text.lower()
            if any(term in response_text for term in ['captcha', 'enter the characters', 'robot check', 'enter the characters you see below']):
                print(f"CAPTCHA or bot detection triggered (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    # Save the response for debugging
                    with open('captcha_page.html', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print("Saved CAPTCHA page to captcha_page.html")
                    return None
                # Wait longer between retries
                time.sleep(5 * (attempt + 1))
                continue
                
            # Save the response for debugging
            with open('last_amazon_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get product title - try multiple selectors
            title = None
            title_selectors = [
                'span#productTitle',
                'h1#title',
                'h1.a-size-large',
                'h1.a-size-medium',
                'h1.a-text-ellipsis',
                'div#titleBlock h1',
                'div#titleSection h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    title = title_elem.get_text().strip()
                    break
            
            if not title:
                print("Could not find product title")
                return None
            
            # Get product price - try multiple selectors
            price = None
            price_selectors = [
                'span.a-price-whole',
                'span.a-offscreen',
                'span#priceblock_ourprice',
                'span#priceblock_dealprice',
                'span#priceblock_saleprice',
                'span.a-color-price',
                'span.a-price-symbol + span',
                'span[data-a-color="price"]',
                'span[data-a-color="price"] span'
            ]
            
            for selector in price_selectors:
                price_elems = soup.select(selector)
                for elem in price_elems:
                    price_text = elem.get_text().strip()
                    # Extract numbers and decimal point
                    price_str = ''.join(c for c in price_text if c.isdigit() or c in '.,')
                    price_str = price_str.replace(',', '').replace('..', '.')
                    if price_str.count('.') > 1:  # Handle cases like 1.234.56
                        parts = price_str.split('.')
                        price_str = '.'.join(parts[:-1]) + parts[-1]
                    try:
                        price = float(price_str)
                        if price > 0:  # Only accept positive prices
                            break
                    except (ValueError, AttributeError):
                        continue
                if price:
                    break
            
            # Get product image
            image_url = None
            image_selectors = [
                'img#landingImage',
                'img#imgBlkFront',
                'img#main-image',
                'img.a-dynamic-image',
                'div#imgTagWrapperId img',
                'div#main-image-container img',
                'div#imageBlock img',
                'div#img-canvas img'
            ]
            
            for selector in image_selectors:
                img = soup.select_one(selector)
                if img:
                    image_url = (
                        img.get('data-old-hires') or 
                        img.get('data-a-dynamic-image') or 
                        img.get('src') or 
                        img.get('data-src')
                    )
                    if image_url and image_url.startswith('http'):
                        break
            
            # If we still don't have an image URL, try to extract from JSON data
            if not image_url:
                try:
                    import json
                    for img in soup.find_all('img', {'data-a-dynamic-image': True}):
                        image_data = json.loads(img['data-a-dynamic-image'])
                        if image_data:
                            image_url = next(iter(image_data.keys()))
                            if image_url.startswith('http'):
                                break
                except Exception as e:
                    print(f"Error extracting image from JSON data: {e}")
            
            # If we still don't have an image, use a placeholder
            if not image_url:
                image_url = 'https://via.placeholder.com/300?text=No+Image+Available'
            
            return {
                'title': title,
                'price': price,
                'image_url': image_url,
                'url': url,
                'last_updated': datetime.utcnow()
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            print(f"Error fetching product info (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
    
    return None

def check_prices():
    print("Checking prices...")
    for product in products.find():
        try:
            product_info = get_amazon_product_info(product['url'])
            if product_info and product_info['price'] is not None:
                # Update product with new price and history
                price_history = product.get('price_history', [])
                price_history.append({
                    'price': product_info['price'],
                    'date': datetime.utcnow()
                })
                
                update_data = {
                    'current_price': product_info['price'],
                    'last_updated': datetime.utcnow(),
                    'price_history': price_history[-30:],  # Keep last 30 price points
                    'title': product_info['title'],
                    'image_url': product_info['image_url']
                }
                
                # Only update image if we got a new one
                if not product_info['image_url']:
                    update_data.pop('image_url')
                
                products.update_one(
                    {'_id': product['_id']},
                    {'$set': update_data}
                )
                
                # Check if price dropped below threshold
                if product_info['price'] <= product['threshold_price'] and product.get('alert_sent', False) is False:
                    send_price_alert(product['email'], product_info, product['threshold_price'])
                    products.update_one(
                        {'_id': product['_id']},
                        {'$set': {'alert_sent': True}}
                    )
                elif product_info['price'] > product['threshold_price'] and product.get('alert_sent', True) is True:
                    # Reset alert if price goes back up
                    products.update_one(
                        {'_id': product['_id']},
                        {'$set': {'alert_sent': False}}
                    )
        except Exception as e:
            print(f"Error processing product {product.get('_id')}: {e}")

def send_price_alert(email, product_info, threshold_price):
    try:
        if not all([EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'], email]):
            print("Email configuration is incomplete. Cannot send price alert.")
            return
            
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = email
        msg['Subject'] = f"Price Drop Alert: {product_info['title'][:50]}..."
        
        body = f"""
        <div style="font-family: 'Poppins', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border-radius: 10px; background: #f8f9fa; color: #333;">
            <div style="background: linear-gradient(135deg, #6c63ff, #4a45b1); padding: 30px; border-radius: 10px 10px 0 0; color: white; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">🎉 Price Drop Alert!</h1>
            </div>
            <div style="padding: 30px; background: white; border-radius: 0 0 10px 10px;">
                <h2 style="color: #4a45b1; margin-top: 0;">{product_info['title']}</h2>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 16px; color: #666;">Current Price</p>
                    <p style="font-size: 32px; font-weight: bold; color: #6c63ff; margin: 0;">${product_info['price']:.2f}</p>
                    <p style="margin: 5px 0 0 0; color: #666;">Your Target: ${threshold_price:.2f}</p>
                </div>
                
                <p style="margin-bottom: 25px; line-height: 1.6;">The price has dropped below your target! Don't miss this great deal.</p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{product_info['url']}" style="display: inline-block; padding: 12px 30px; background: #6c63ff; color: white; text-decoration: none; border-radius: 50px; font-weight: 600; transition: all 0.3s ease;">
                        View on Amazon
                    </a>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="color: #999; font-size: 14px; margin: 0;">Happy Shopping! 🛍️</p>
                </div>
            </div>
        </div>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
            server.send_message(msg)
            print(f"Price alert sent to {email}")
    except Exception as e:
        print(f"Error sending email: {e}")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  


schedule.every(1).hours.do(check_prices)


scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
   
    with app.app_context():
        mongo.db.price_history.create_index([('product_id', 1), ('date', 1)])
    
    app.run(debug=False, port=5001)
