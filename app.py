import matplotlib

from seeder import run_external_seed

matplotlib.use('Agg')  # Force non-GUI backend before any other matplotlib import
import time
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from dashboard import dashboard_blueprint
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import werkzeug.exceptions




from utils import timestamp_to_str  # Import our custom filter



REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'] # 'Labels' - נסביר עוד רגע
)

# 2. Requests (Rate + Errors):
# נוסיף Labels כדי שנוכל לפלטר לפי מתודה, ראוט וסטטוס קוד
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'http_status']
)


run_external_seed()



def create_app():
    run_external_seed()

    app = Flask(__name__)

    # -------------------------
    # Logging Configuration
    # -------------------------
    if not os.path.exists('logs'):
        os.makedirs('logs')

    error_handler = RotatingFileHandler('logs/error.log', maxBytes=1000000, backupCount=3)
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    app.logger.addHandler(error_handler)

    usage_handler = RotatingFileHandler('logs/access.log', maxBytes=1000000, backupCount=3)
    usage_handler.setLevel(logging.INFO)
    usage_formatter = logging.Formatter('%(asctime)s - %(message)s')
    usage_handler.setFormatter(usage_formatter)
    usage_logger = logging.getLogger('usage')
    usage_logger.addHandler(usage_handler)
    usage_logger.setLevel(logging.INFO)

    @app.before_request
    def log_request_info():
        from flask import request
        usage_logger.info(f"{request.remote_addr} - {request.method} {request.url}")

    @app.before_request
    def start_timer():
        """מתחיל טיימר בתחילת כל בקשה."""
        # שים לב, זהו Hook שני של before_request.
        # פלאסק יריץ את שניהם (גם את log_request_info וגם את זה).
        request.start_time = time.time()

    @app.after_request
    def record_metrics(response):
        """רושם מטריקות בסוף כל בקשה (שלא הסתיימה בשגיאה)."""

        # 1. חישוב משך הבקשה (Duration)
        latency = time.time() - request.start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(latency)

        # 2. ספירת הבקשה (Rate + Errors)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            http_status=response.status_code
        ).inc()

        return response

    @app.errorhandler(werkzeug.exceptions.InternalServerError)
    def handle_500(e):
        """מטפל ספציפית בשגיאות 500 כדי לוודא שהן נספרות."""
        # ה-Hook של after_request לא רץ אוטומטית במקרה של 500

        # אנחנו לא מחשבים Latency כאן, רק סופרים את השגיאה
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            http_status=500
        ).inc()

        # מחזיר את תגובת השגיאה המקורית
        return e

    @app.route('/metrics')
    def metrics():
        """זה ה-Endpoint שפרומיתאוס יגרד (scrape)."""
        return generate_latest(REGISTRY)


    # Register our blueprint
    app.register_blueprint(dashboard_blueprint)

    # Register custom Jinja2 filter so templates can use |timestamp_to_str
    app.jinja_env.filters['timestamp_to_str'] = timestamp_to_str

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', debug=True)
