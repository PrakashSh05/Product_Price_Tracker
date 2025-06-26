from flask import Blueprint, render_template, jsonify, redirect, url_for, request
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from datetime import datetime
from extensions import mongo

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    user_products = list(mongo.db.products.find({'user_id': current_user.id}).sort('last_updated', -1))
    # Convert ObjectId to string for JSON serialization
    for product in user_products:
        product['_id'] = str(product['_id'])
    return render_template('dashboard.html', products=user_products)

@main.route('/track', methods=['POST'])
@login_required
def track_product():
    print("\n=== New Track Product Request ===")
    print(f"Current User: {current_user.email if current_user.is_authenticated else 'Not authenticated'}")
    
    try:
        data = request.get_json()
        print(f"Request data: {data}")
        
        if not data:
            print("Error: No data provided")
            return jsonify({'error': 'No data provided'}), 400
            
        url = data.get('url')
        print(f"URL from request: {url}")
        
        try:
            threshold_price = float(data.get('threshold_price', 0))
            print(f"Threshold price: {threshold_price}")
        except (ValueError, TypeError) as e:
            print(f"Error parsing threshold price: {e}")
            return jsonify({'error': 'Invalid price format'}), 400
        
        if not url or not isinstance(url, str) or len(url) < 10:
            print(f"Error: Invalid URL format: {url}")
            return jsonify({'error': 'Invalid or missing URL'}), 400
            
        if threshold_price <= 0:
            print(f"Error: Invalid threshold price: {threshold_price}")
            return jsonify({'error': 'Price threshold must be greater than 0'}), 400
        
        # Check if product is already being tracked by this user
        print(f"Checking if product is already tracked by user {current_user.email}")
        existing = mongo.db.products.find_one({
            'user_id': current_user.id,
            'url': url
        })
        
        if existing:
            print(f"Product already tracked with ID: {existing['_id']}")
            return jsonify({
                'error': 'This product is already being tracked',
                'product_id': str(existing['_id'])
            }), 400
        
        # Get product info
        print("\n--- Fetching product info from Amazon ---")
        from app import get_amazon_product_info  # Import here to avoid circular import
        print(f"Calling get_amazon_product_info with URL: {url}")
        product_info = get_amazon_product_info(url)
        print(f"Product info received: {product_info is not None}")
        
        if not product_info:
            print("Error: Failed to fetch product information")
            # Save the last response for debugging
            try:
                with open('last_error.html', 'w', encoding='utf-8') as f:
                    f.write(open('last_amazon_response.html', 'r', encoding='utf-8').read())
                print("Saved last error response to last_error.html")
            except Exception as e:
                print(f"Could not save error response: {e}")
                
            return jsonify({'error': 'Could not fetch product information from the provided URL'}), 400
            
        if product_info.get('price') is None:
            return jsonify({
                'error': 'Could not determine product price. The product might be out of stock or unavailable.',
                'details': 'Price not found on the page'
            }), 400
        
        # Prepare product data
        product_data = {
            'user_id': current_user.id,
            'url': url,
            'email': current_user.email,
            'threshold_price': threshold_price,
            'current_price': product_info['price'],
            'title': product_info['title'],
            'image_url': product_info['image_url'],
            'last_updated': datetime.utcnow(),
            'price_history': [{
                'price': product_info['price'],
                'date': datetime.utcnow()
            }],
            'alert_sent': False,
            'created_at': datetime.utcnow()
        }
        
        # Insert into database
        try:
            result = mongo.db.products.insert_one(product_data)
            return jsonify({
                'message': 'Product is now being tracked!',
                'product_id': str(result.inserted_id),
                'product_info': {
                    'title': product_info['title'],
                    'price': product_info['price'],
                    'image_url': product_info['image_url']
                }
            })
        except Exception as e:
            print(f"Database error: {e}")
            return jsonify({'error': 'Failed to save product to database'}), 500
    except Exception as e:
        print(f"Error tracking product: {e}")
        return jsonify({'error': 'An error occurred while tracking the product'}), 500

@main.route('/product/<product_id>/history')
@login_required
def product_history(product_id):
    try:
        product = mongo.db.products.find_one({'_id': ObjectId(product_id), 'user_id': current_user.id})
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        history = product.get('price_history', [])
        # Convert datetime to string for JSON serialization
        for entry in history:
            if 'date' in entry and isinstance(entry['date'], datetime):
                entry['date'] = entry['date'].isoformat()
        
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/product/<product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    try:
        result = mongo.db.products.delete_one({'_id': ObjectId(product_id), 'user_id': current_user.id})
        if result.deleted_count == 0:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({'message': 'Product deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
