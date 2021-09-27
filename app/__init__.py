import os

__version__ = '0.0.2'
__service__ = os.environ.get("SERVICE_NAME", "Rocket Manager")
__root__ = os.environ.get("ROOT_PATH", "/")
__startup_time__ = int(os.environ.get("STARTUP_TIME", "10"))

USER_SECRET = os.environ.get("SECRET_KEY", "e9629f658c37859ab9d74680a3480b99265c7d4c89224280cb44a255c320661f")
USER_URL = os.environ.get("USER_URL", "http://user_manager/token")

# Rocket specific config
MIN_ENGINES = int(os.environ.get("MIN_ENGINES", "1"))
MAX_ENGINES = int(os.environ.get("MAX_ENGINES", "8"))
MIN_HEIGHT = int(os.environ.get("MIN_HEIGHT", "30"))
MAX_HEIGHT = int(os.environ.get("MAX_HEIGHT", "200"))
RF_DENSITY = float(os.environ.get("RF_DENSITY", "750"))
WALL_THICKNESS = float(os.environ.get("WALL_THICKNESS", "0.03"))
TIME_DELTA = float(os.environ.get("TIME_DELTA", "1.0"))
MASS_FLOW = float(os.environ.get("MASS_FLOW", "2500"))
