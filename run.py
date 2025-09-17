"""Main entry point for running the Flask development server."""

import os

from app import create_app

app = create_app()

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)  # nosec B104
