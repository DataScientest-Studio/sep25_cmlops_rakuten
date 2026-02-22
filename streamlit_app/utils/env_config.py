"""
Environment configuration loader for Streamlit app.

This module ensures environment variables are loaded from the .env file
at the project root, since Streamlit doesn't automatically load .env files.
"""
import os
from pathlib import Path


def load_env_vars():
    """
    Load environment variables from .env file if not already loaded.
    
    Priority:
    1. Streamlit secrets (st.secrets)
    2. Environment variables
    3. .env file at project root
    """
    # Check if already loaded (avoid reloading)
    if os.getenv('_ENV_LOADED'):
        return
    
    # Try to use python-dotenv if available
    try:
        from dotenv import load_dotenv
        
        # Find .env file at project root (2 levels up from this file)
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(env_path, override=False)  # Don't override existing vars
            os.environ['_ENV_LOADED'] = '1'
    except ImportError:
        # python-dotenv not available, manually parse .env
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Only set if not already set
                        if key not in os.environ:
                            os.environ[key] = value
            os.environ['_ENV_LOADED'] = '1'


def get_db_config():
    """
    Get database configuration from secrets or environment variables.
    
    Returns:
        dict: Database configuration with keys: host, port, database, user, password
    """
    # Ensure environment is loaded
    load_env_vars()
    
    # Try Streamlit secrets first (only if streamlit is available)
    try:
        import streamlit as st
        if 'database' in st.secrets:
            return {
                'host': st.secrets['database'].get('host', 'localhost'),
                'port': int(st.secrets['database'].get('port', 5432)),
                'database': st.secrets['database'].get('database', 'rakuten_db'),
                'user': st.secrets['database'].get('user', 'rakuten_user'),
                'password': st.secrets['database'].get('password', 'rakuten_pass')
            }
    except (ImportError, AttributeError, KeyError, FileNotFoundError):
        pass
    
    # Fall back to environment variables
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'rakuten_db'),
        'user': os.getenv('POSTGRES_USER', 'rakuten_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'rakuten_pass')
    }


def get_env(key, default=None):
    """
    Get environment variable with automatic .env loading.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        str: Environment variable value or default
    """
    load_env_vars()
    return os.getenv(key, default)


CATEGORY_NAMES = {
    10: "Livres",
    40: "Jeux video",
    50: "Accessoires gaming",
    60: "Consoles retro",
    1140: "Figurines",
    1160: "Cartes de collection",
    1180: "Jeux de plateau & Figurines",
    1280: "Jouets & Peluches",
    1281: "Jeux de construction",
    1300: "Modelisme & Drones",
    1301: "Vetements bebe",
    1302: "Jeux d'exterieur enfants",
    1320: "Puericulture",
    1560: "Ameublement & Literie",
    1920: "Linge & Decoration maison",
    1940: "Epicerie & Gourmandises",
    2060: "Decoration & Objets",
    2220: "Animalerie",
    2280: "Magazines & Revues",
    2403: "Livres anciens & Partitions",
    2462: "Consoles & Jeux video (packs)",
    2522: "Fournitures de bureau",
    2582: "Mobilier d'exterieur",
    2583: "Piscine & Jardin",
    2585: "Outillage & Bricolage",
    2705: "Litterature & Essais",
    2905: "Jeux video dematerialises",
}


def get_category_label(code):
    """Return 'code - Name' if known, otherwise just the code as string."""
    name = CATEGORY_NAMES.get(int(code), None)
    return f"{code} - {name}" if name else str(code)
