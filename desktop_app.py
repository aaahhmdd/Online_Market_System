import threading
import webview
from distributed_market_system import app  # Your Flask app

def run_flask():
    # Run Flask app; use port 5000 or change if needed
    app.run()

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Create a PyWebView window showing the Flask app
    webview.create_window('Marketplace Desktop App', 'http://127.0.0.1:5000')
    webview.start()
