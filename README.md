# BAAR-C v1.0: Blockchain-Associated Artwork Registry - Cryptographic

**Welcome to BAAR-C**, a Web3-ready tool designed to prepare digital artwork for NFT creation. BAAR-C (Blockchain-Associated Artwork Registry - Cryptographic) streamlines the process of watermarking, cryptographically signing, and uploading images to IPFS, ensuring your artwork is authenticated and tracked before minting as Non-Fungible Tokens (NFTs). Built with Python, this v1.0 release offers a solid foundation for creators stepping into the blockchain art space.

## Features
- **Cryptographic Signing**: Generates RSA key pairs and signs artwork hashes to prove authenticity.
- **Watermarking**: Adds a fixed-size logo in a random corner and a unique BAAR-C key (derived from your public key) with configurable exclusion zones.
- **IPFS Integration**: Uploads processed images to the InterPlanetary File System (IPFS) and logs the Content Identifier (CID) for decentralized storage.
- **Inventory Tracking**: Records file details, hashes, and IPFS CIDs in an Excel file for metadata management.
- **Web3 Ready**: Prepares artwork for NFT minting with verifiable signatures and IPFS-hosted assets.
- **Error Handling**: Ensures original images remain untouched until successful processing, with clear user feedback.

## Purpose
BAAR-C v1.0 is your pre-minting companion in the NFT ecosystem. Whether you’re an artist, collector, or developer, this tool helps you:
- Authenticate digital artwork with cryptographic signatures.
- Store assets on IPFS for blockchain linking.
- Track your creations in a simple inventory before minting on platforms like Ethereum, Solana, or others.

This is the first step toward a robust Web3 art registry—v2 will bring even more features!

## Prerequisites
Before diving in, ensure you have:
- **Python 3.8+**: The script runs on modern Python versions.
- **IPFS**: Installed and running (desktop client or CLI daemon). [Download here](https://ipfs.io/#install).
- **Dependencies**: Install required Python libraries (see Installation).

## Installation
1. **Clone the Repository**:
- git clone https://github.com/yourusername/baar-c.git
- cd baar-c
   
   
2. Install Python Dependencies:
- pip install -r requirements.txt
   
**Or manually install** :
- pip install pillow cryptography watchdog ipfshttpclient python-magic pandas openpyxl

3. Set Up IPFS:
- Install IPFS (e.g., via go-ipfs or desktop app).

- Start the IPFS daemon in a separate terminal:
- ipfs daemon

4. Prepare Folders:
- The script auto-creates unsigned, signed, keys, cache, and resources/fonts folders if missing.

- Place your logo in watermark/baar-clogo.jpg (create the watermark folder if needed).

5. Optional Font:
- Add .ttf fonts to resources/fonts for BAAR-C key text, or place Roboto-Regular.ttf in the root directory as a fallback.

## Usage
1. Configure config.ini:
- Edit config.ini to adjust paths, logo size, exclusion zones, etc. (See Configuration below.)

## Default settings work out of the box.

2. Run the Script:
- python baar-c.py

## You’ll be prompted: Use existing key pair? (y/n). Choose y to reuse keys or n to generate new ones.

3. Add Artwork:
- Drop .jpg files into the unsigned folder.

## The script processes each file, adding watermarks, signing, and uploading to IPFS.

4. Check Outputs:
- Signed Images: Processed .png files appear in signed.

- Cache: Original .jpg files move to cache after success.

- Inventory: Details are saved to inventory.xlsx.

- Logs: See log_<timestamp>.txt for processing details.

5. Stop: Press Ctrl+C to stop monitoring.

## On Error
**If processing fails (e.g., IPFS down), the image stays in unsigned, a message logs ("No changes made to <filename>. Try again."), and the program exits. Fix the issue and restart.**

**Configuration (config.ini)**
## Customize BAAR-C via config.ini:
[Paths]
watch_folder = ./unsigned        # Where to drop unprocessed .jpg files
output_folder = ./signed         # Where processed .png files go
keys_folder = ./keys             # Stores RSA key pairs
fonts_folder = ./resources/fonts # Optional .ttf fonts for BAAR-C key
cache_folder = ./cache           # Processed originals move here
logo_path = ./watermark/baar-clogo.jpg # Your logo file

[Settings]
baarckey_font_size = 20          # Font size for BAAR-C key text
passphrase_prompt = True         # Prompt for passphrase if key loading fails
passphrase = baar-c_ode          # Default passphrase for private key
excel_file = ./inventory.xlsx    # Inventory output file
logo_size = 200                  # Logo size in pixels (square)

[Metadata]
copyright = BAAR-C by Panicked to Prepared # Embedded metadata
authors = BAAR-C                           # Creator name
program_name = BAAR-C                     # Tool name

[ExclusionZones]
zone1 = 512,0,767                # Grid column exclusion (x_start, y_start, x_end)
zone2 = 768,0,1023
zone3 = 1024,0,1279
zone4 = 1280,0,1535
center = 0.4,0.4,0.6,0.6         # Center exclusion (relative x_start, y_start, x_end, y_end)

**Exclusion Zones: Prevent BAAR-C key placement in grid columns (e.g., 512-767px) and center (20% of image dimensions). Logo placement (corners) ignores these.**

## Output
**Signed Image: .png with logo in a corner and BAAR-C key elsewhere.**

**Inventory.xlsx: Columns include**:
- File Name

- Signed Hash

- IPFS-Uploaded Hash 

- IPFS CID

- Logo Position

- BAAR-C Key

- BAAR-C Key Position

- Timestamp

**Log File: Detailed steps (e.g., log_0314251803.txt).**

## Example Workflow

1. Drop art.jpg into unsigned.

2. BAAR-C:
- Copies to signed/art.png.

- Adds logo (e.g., top-left) and BAAR-C key.

- Signs the hash.

- Uploads to IPFS (CID: Qm...).

- Updates inventory.xlsx.

- Moves art.jpg to cache.

3. Use the CID and signature for NFT minting on your blockchain of choice.

## Known Limitations (v1)

Excel Formatting: Overwrites inventory.xlsx, losing manual styles. Move to a formatted file manually.

Font Fallback: Requires Roboto-Regular.ttf if fonts_folder is empty.

Single File Processing: Stops on error; restart needed.

IPFS Dependency: Must be running locally.

## Roadmap (v2 Ideas)





## Contributing

This is an open-source project! Fork it, submit PRs, or open issues on GitHub. Ideas for Web3 enhancements are welcome!

## License

MIT License—use it, modify it, share it. See LICENSE file.

## Credits

- Panicked To Prepared
- Inspired by the Web3 NFT community