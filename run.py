import os
from app import create_app

config_name = os.environ.get("FLASK_ENV", "development") # Default to "development" if FLASK_ENV is not set.
app = create_app(config_name)


if __name__ == "__main__": # Only run the app if this script is executed directly (not imported as a module).
    app.run(debug=True, port = 5001) #doesn't collide with AirPlay server.