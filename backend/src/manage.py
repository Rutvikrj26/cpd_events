#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys



def main():
    """Run administrative tasks."""
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        result = load_dotenv(env_path)
        raise Exception(f"DEBUG FORCE CRASH: env_path={env_path}, load_dotenv={result}, ZOOM_ID={os.environ.get('ZOOM_CLIENT_ID')}")
    except ImportError:
        pass

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Are you sure it's installed?") from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
