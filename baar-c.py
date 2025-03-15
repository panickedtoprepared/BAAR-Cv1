import os
import time
import random
import hashlib
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw, ImageFont
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import logging
import shutil
from datetime import datetime
import ipfshttpclient
import magic
import configparser
import getpass
import pandas as pd

# Get current timestamp for key and log file naming
timestamp = datetime.now().strftime("%m%d%y%H%M")

# Setup logging to file and console
log_file = os.path.join(os.path.dirname(__file__), f"log_{timestamp}.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Load configuration from config.ini
config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
if not os.path.exists(config_file):
    raise FileNotFoundError(f"Configuration file {config_file} not found.")
config.read(config_file)

# Get base directory
BASE_DIR = os.path.dirname(__file__)

# Folder paths from config
WATCH_FOLDER = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['watch_folder']))
OUTPUT_FOLDER = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['output_folder']))
KEYS_FOLDER = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['keys_folder']))
FONTS_FOLDER = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['fonts_folder']))
CACHE_FOLDER = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['cache_folder']))
PRIVATE_KEY_FILE = os.path.join(KEYS_FOLDER, f"{timestamp}_privatekey.pem")
PUBLIC_KEY_FILE = os.path.join(KEYS_FOLDER, f"{timestamp}_publickey.pem")
LOGO_PATH = os.path.normpath(os.path.join(BASE_DIR, config['Paths']['logo_path']))
PASSPHRASE = config['Settings']['passphrase']
EXCEL_FILE = os.path.normpath(os.path.join(BASE_DIR, config['Settings']['excel_file']))

# Metadata from config
COPYRIGHT = config['Metadata']['copyright']
AUTHORS = config['Metadata']['authors']
PROGRAM_NAME = config['Metadata']['program_name']

# Configurable settings
BAARCKEY_FONT_SIZE = config.getint('Settings', 'baarckey_font_size')
LOGO_SIZE = config.getint('Settings', 'logo_size')

# Exclusion zones from config
def get_exclusion_zones(img_width, img_height):
    zones = []
    for key in config['ExclusionZones']:
        if key != 'center':
            x_start, y_start, x_end = map(int, config['ExclusionZones'][key].split(','))
            zones.append((x_start, y_start, x_end, img_height))
        else:
            values = config['ExclusionZones']['center'].split(',')
            x_start, y_start, x_end, y_end = map(float, values)
            zones.append((
                int(img_width * x_start), int(img_height * y_start),
                int(img_width * x_end), int(img_height * y_end)
            ))
    return zones

def ensure_folders_exist():
    for folder in [WATCH_FOLDER, OUTPUT_FOLDER, KEYS_FOLDER, FONTS_FOLDER, CACHE_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logging.info(f"Created folder: {folder}")

def get_random_font():
    font_files = [f for f in os.listdir(FONTS_FOLDER) if f.lower().endswith('.ttf')]
    if not font_files:
        default_font = os.path.join(BASE_DIR, "Roboto-Regular.ttf")
        if not os.path.exists(default_font):
            logging.error(f"No .ttf fonts found in {FONTS_FOLDER} and default font {default_font} missing.")
            raise FileNotFoundError(f"Default font {default_font} not found.")
        logging.warning(f"No .ttf fonts found in {FONTS_FOLDER}, using default")
        return default_font
    return os.path.join(FONTS_FOLDER, random.choice(font_files))

def is_ipfs_running():
    try:
        client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        client.close()
        return True
    except (ipfshttpclient.exceptions.ConnectionError, Exception):
        return False

def start_ipfs_daemon():
    if not is_ipfs_running():
        logging.info("IPFS daemon not running, attempting to start it...")
        try:
            if os.name == 'nt':
                subprocess.Popen(['start', 'ipfs', 'daemon'], shell=True)
            else:
                subprocess.Popen(['ipfs', 'daemon'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(30):
                time.sleep(1)
                if is_ipfs_running():
                    logging.info("IPFS daemon started successfully.")
                    return True
            logging.error("Failed to start IPFS daemon within 30 seconds. Try running 'ipfs daemon' manually first.")
            return False
        except FileNotFoundError:
            logging.error("IPFS executable not found. Ensure IPFS is installed and in PATH.")
            return False
        except Exception as e:
            logging.error(f"Error starting IPFS daemon: {e}")
            return False
    return True

def connect_ipfs():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            try:
                client.files.stat('/signed-images')
            except ipfshttpclient.exceptions.ErrorResponse:
                client.files.mkdir('/signed-images')
            return client
        except Exception as e:
            logging.warning(f"IPFS connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise Exception("Failed to connect to IPFS after retries")

def rectangles_intersect(rect1, rect2):
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2
    return (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2)

class JPGHandler(FileSystemEventHandler):
    def __init__(self, use_existing_keys=False):
        global PASSPHRASE
        if use_existing_keys and os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
            try:
                with open(PRIVATE_KEY_FILE, "rb") as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=PASSPHRASE.encode())
                with open(PUBLIC_KEY_FILE, "rb") as f:
                    public_key = serialization.load_pem_public_key(f.read())
                self.private_key = private_key
                self.public_key = public_key
                logging.info(f"Using existing key pair: {os.path.basename(PRIVATE_KEY_FILE)}, {os.path.basename(PUBLIC_KEY_FILE)}")
            except ValueError as e:
                logging.error(f"Failed to load private key with passphrase: {e}")
                if config.getboolean('Settings', 'passphrase_prompt', fallback=True):
                    PASSPHRASE = getpass.getpass("Enter the passphrase for the private key: ")
                    try:
                        with open(PRIVATE_KEY_FILE, "rb") as f:
                            private_key = serialization.load_pem_private_key(f.read(), password=PASSPHRASE.encode())
                        with open(PUBLIC_KEY_FILE, "rb") as f:
                            public_key = serialization.load_pem_public_key(f.read())
                        self.private_key = private_key
                        self.public_key = public_key
                    except ValueError as e:
                        logging.error(f"Passphrase incorrect or key corrupted: {e}")
                        raise Exception("Could not load private key.")
                else:
                    raise Exception("Passphrase incorrect and prompting disabled.")
        else:
            logging.info("Generating new key pair...")
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key()
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(PASSPHRASE.encode())
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(PRIVATE_KEY_FILE, "wb") as f:
                f.write(private_pem)
            with open(PUBLIC_KEY_FILE, "wb") as f:
                f.write(public_pem)
            self.private_key = private_key
            self.public_key = public_key
            logging.info(f"Generated new key pair: {os.path.basename(PRIVATE_KEY_FILE)}, {os.path.basename(PUBLIC_KEY_FILE)}")

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        if file_path.lower().endswith('.jpg'):
            logging.info(f"New file detected: {file_path}")
            self.wait_for_file_stability(file_path)
            self.process_image(file_path)

    def wait_for_file_stability(self, file_path):
        while True:
            size1 = os.path.getsize(file_path)
            time.sleep(0.1)
            size2 = os.path.getsize(file_path)
            if size1 == size2:
                break

    def process_image(self, jpg_path):
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(jpg_path)
            if file_type != "image/jpeg":
                logging.error(f"Invalid file type for {jpg_path}: {file_type}")
                return

            output_file = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(jpg_path))[0] + ".png")
            shutil.copy2(jpg_path, output_file)
            img = Image.open(output_file).convert("RGB")
            os.utime(output_file, times=(time.time(), time.time()))

            # Add watermark/logo in a corner
            img = Image.open(output_file).convert("RGBA")
            logo = Image.open(LOGO_PATH).convert("RGBA")
            img_width, img_height = img.size
            logo = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
            logo_width, logo_height = LOGO_SIZE, LOGO_SIZE

            corners = [
                (0, 0),  # Top-left
                (img_width - logo_width, 0),  # Top-right
                (0, img_height - logo_height),  # Bottom-left
                (img_width - logo_width, img_height - logo_height)  # Bottom-right
            ]
            random.shuffle(corners)

            # Add BAAR-C key
            draw = ImageDraw.Draw(img)
            baarckey_font = ImageFont.truetype(get_random_font(), BAARCKEY_FONT_SIZE)
            baarckey_text = f"baar-c key // {hashlib.sha256(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )).hexdigest()[:16]} //"
            baarckey_bbox = draw.textbbox((0, 0), baarckey_text, font=baarckey_font)
            baarckey_text_width = baarckey_bbox[2] - baarckey_bbox[0]
            baarckey_text_height = baarckey_bbox[3] - baarckey_bbox[1]

            exclusion_zones = get_exclusion_zones(img_width, img_height)
            max_attempts = 200
            for _ in range(max_attempts):
                baarckey_x = random.randint(0, img_width - baarckey_text_width)
                baarckey_y = random.randint(0, img_height - baarckey_text_height)
                baarckey_rect = (baarckey_x, baarckey_y, baarckey_text_width, baarckey_text_height)
                overlaps = any(rectangles_intersect(baarckey_rect, zone) for zone in exclusion_zones)
                if not overlaps:
                    break
            else:
                logging.warning("Could not place BAAR-C key without overlapping exclusion zones")
            draw.text((baarckey_x, baarckey_y), baarckey_text, font=baarckey_font, fill=(255, 255, 255, 128))

            # Place logo, avoiding BAAR-C key
            logo_x, logo_y = None, None
            baarckey_rect = (baarckey_x, baarckey_y, baarckey_text_width, baarckey_text_height)
            for corner_x, corner_y in corners:
                logo_rect = (corner_x, corner_y, logo_width, logo_height)
                if not rectangles_intersect(logo_rect, baarckey_rect):
                    logo_x, logo_y = corner_x, corner_y
                    break
            if logo_x is None or logo_y is None:
                logging.warning("Could not place logo in any corner without overlapping BAAR-C key")
                logo_x, logo_y = corners[0]  # Fallback to first corner
            img.paste(logo, (logo_x, logo_y), logo)
            img.save(output_file, "PNG")

            # Sign hash (after BAAR-C key)
            with open(output_file, "rb") as f:
                image_data = f.read()
                signed_hash = hashlib.sha256(image_data).hexdigest()
            signature_base = (LOGO_PATH.encode() + signed_hash.encode())
            signature = self.private_key.sign(
                signature_base,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )

            # Upload to IPFS
            client = connect_ipfs()
            res = client.add(output_file)
            ipfs_cid = res['Hash']
            client.files.write(f"/signed-images/{os.path.basename(output_file)}", output_file, create=True)

            # Compute hash of IPFS-uploaded image
            with open(output_file, "rb") as f:
                ipfs_hash = hashlib.sha256(f.read()).hexdigest()

            # Display hashes
            logging.info(f"Processed {os.path.basename(jpg_path)}:")
            logging.info(f"  Signed Hash (post-BAAR-C key): {signed_hash}")
            logging.info(f"  IPFS-Uploaded Hash: {ipfs_hash}")
            logging.info(f"  IPFS CID: {ipfs_cid}")

            # Save to Excel with overwrite method
            record = {
                "File Name": os.path.basename(output_file),
                "Signed Hash": signed_hash,
                "IPFS-Uploaded Hash": ipfs_hash,
                "IPFS CID": ipfs_cid,
                "Logo Position": f"({logo_x}, {logo_y})",
                "BAAR-C Key": baarckey_text,
                "BAAR-C Key Position": f"({baarckey_x}, {baarckey_y})",
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            df = pd.DataFrame([record])
            if os.path.exists(EXCEL_FILE):
                existing_df = pd.read_excel(EXCEL_FILE)
                df = pd.concat([existing_df, df], ignore_index=True)
            df.to_excel(EXCEL_FILE, index=False)
            logging.info(f"Saved record to {EXCEL_FILE}")

            # Move to cache only after successful IPFS upload
            cache_file = os.path.join(CACHE_FOLDER, os.path.basename(jpg_path))
            shutil.move(jpg_path, cache_file)
            logging.info(f"Moved processed original to cache: {cache_file}")

            client.close()

        except Exception as e:
            logging.error(f"Error processing {jpg_path}: {e}")
            logging.info(f"No changes made to {os.path.basename(jpg_path)}. Try again.")
            if os.path.exists(output_file):
                os.remove(output_file)  # Clean up failed output
            sys.exit(1)  # Stop program on error

def start_monitoring():
    if not os.path.exists(LOGO_PATH):
        logging.error(f"Logo file {LOGO_PATH} not found.")
        return

    use_existing = input("Use existing key pair? (y/n): ").lower().startswith('y')
    event_handler = JPGHandler(use_existing_keys=use_existing)

    if not start_ipfs_daemon():
        logging.error("Cannot proceed without IPFS running. Exiting.")
        return
    
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()
    logging.info(f"Started monitoring {WATCH_FOLDER}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Monitoring stopped")
    observer.join()

if __name__ == "__main__":
    ensure_folders_exist()
    if not os.path.exists(WATCH_FOLDER):
        logging.error(f"Folder {WATCH_FOLDER} does not exist. Please create it.")
    else:
        start_monitoring()