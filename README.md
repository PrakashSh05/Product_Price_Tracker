# Amazon Price Tracker

A web application that tracks Amazon product prices and sends email notifications when prices drop below a specified threshold.

## Features

- Track any Amazon product by URL
- Set price drop alerts
- View price history with interactive charts
- Receive email notifications
- Clean, responsive UI built with Bootstrap 5

## Prerequisites

- Python 3.8+
- MongoDB (local or cloud instance)
- Gmail account (for email notifications)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/PrakashSh05/Product_Price_Tracker
   cd amazon-price-tracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration
   - For Gmail, you'll need to generate an App Password: [Google App Passwords](https://myaccount.google.com/apppasswords)

5. Start MongoDB:
   - Make sure MongoDB is installed and running locally, or update the `MONGODB_URI` in `.env` to point to your MongoDB instance

## Running the Application

1. Start the Flask development server:
   ```bash
   flask run
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. On the home page, enter:
   - Amazon product URL
   - Your email address
   - Your target price

2. Click "Track Product" to start monitoring

3. View your tracked products on the Dashboard

4. You'll receive an email when the price drops below your target

## Project Structure

```
amazon-price-tracker/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in version control)
├── .env.example          # Example environment variables
├── static/               # Static files (CSS, JS, images)
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── script.js
└── templates/            # HTML templates
    ├── base.html
    ├── index.html
    └── dashboard.html
```

## Technologies Used

- **Backend**: Python, Flask
- **Database**: MongoDB
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Web Scraping**: BeautifulSoup4, Requests
- **Scheduling**: schedule

## License

This project is open source and available under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
