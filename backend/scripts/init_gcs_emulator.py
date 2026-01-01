#!/usr/bin/env python
"""
Initialize GCS emulator bucket for local development.

This script creates the required bucket in the fake-gcs-server emulator.
Run this after starting docker-compose to set up local storage.

Usage:
    python scripts/init_gcs_emulator.py
"""

import os
import sys

# Set the emulator host before importing google-cloud-storage
os.environ['STORAGE_EMULATOR_HOST'] = 'http://localhost:4443'

try:
    from google.cloud import storage
except ImportError:
    print("Error: google-cloud-storage not installed")
    print("Install it with: pip install google-cloud-storage")
    sys.exit(1)

BUCKET_NAME = 'cpd-events-local'
PROJECT_ID = 'dev-project'


def init_bucket():
    """Create the storage bucket in the emulator."""
    try:
        # Create client
        client = storage.Client(project=PROJECT_ID)

        # Check if bucket exists
        bucket = client.bucket(BUCKET_NAME)
        if bucket.exists():
            print(f"✓ Bucket '{BUCKET_NAME}' already exists")
            return True

        # Create bucket
        bucket = client.create_bucket(BUCKET_NAME)
        print(f"✓ Created bucket '{BUCKET_NAME}' in GCS emulator")

        # Create common folders
        folders = [
            'certificates/',
            'media/profile_pictures/',
            'media/event_images/',
            'media/certificate_templates/',
        ]

        for folder in folders:
            blob = bucket.blob(folder)
            blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
            print(f"  ✓ Created folder: {folder}")

        print(f"\n✓ GCS emulator initialized successfully!")
        print(f"  Bucket: {BUCKET_NAME}")
        print(f"  Emulator: http://localhost:4443")

        return True

    except Exception as e:
        print(f"✗ Error initializing GCS emulator: {e}")
        return False


if __name__ == '__main__':
    print("Initializing GCS emulator...")
    print(f"Emulator Host: {os.environ.get('STORAGE_EMULATOR_HOST')}")
    print()

    success = init_bucket()
    sys.exit(0 if success else 1)
