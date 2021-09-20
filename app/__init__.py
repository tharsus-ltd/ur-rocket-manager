import os

__version__ = '0.0.1'
__service__ = os.environ.get("SERVICE_NAME", "Rocket Manager")
__root__ = os.environ.get("ROOT_PATH", "/")

# Rocket specific config
MIN_ENGINES = int(os.environ.get("MIN_ENGINES", "1"))
MAX_ENGINES = int(os.environ.get("MAX_ENGINES", "8"))
MIN_HEIGHT = int(os.environ.get("MIN_HEIGHT", "50"))
MAX_HEIGHT = int(os.environ.get("MAX_HEIGHT", "600"))
