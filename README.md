# Discord Photography EXIF Bot

A simple, configurable Discord bot that listens for photo uploads and reposts them with camera metadata (EXIF) in a designated channel. Ideal for photography servers.

---

## Features

- Extracts EXIF data from JPEG, PNG, and Canon CR2 RAW images
- Accepts manual overrides via message
- Reposts images as embedded messages with:
  - Camera Model
  - ISO
  - Aperture
  - Shutter Speed
  - Notes
- Automatically compresses large images
- Easy-to-edit config file

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Shirozy/Discord-Photos-Bot.git
cd photo-exif-bot
````

### 2. Create Your Settings

Rename `settings.example.json` to `settings.json` and fill in your bot token and channel names:

```json
{
  "BOT_TOKEN": "YOUR_DISCORD_BOT_TOKEN",
  "PHOTO_DUMP_CHANNEL": "photo-dump",
  "PHOTOGRAPHY_CHANNEL": "photography",
  "EMBED_COLOR": "#FFB6C1",
  "EMBED_FOOTER": "Photography Corner"
}
```

---

### 3. Install Dependencies

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 photoBot.py
```

#### Windows

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python photoBot.py
```

---

## Example Usage

Upload an image in the `photo-dump` channel with optional metadata:

```
ISO: 400
Aperture: f/1.8
Shutter Speed: 1/250
Note: Taken at the mountains
```

Bot will post an embed in `photography` with details and a download link.

---

## Future Ideas

* Slash command support
* EXIF timestamp
* Image tagging / categorization
* EXIF export to database or CSV
* Web dashboard for settings

---

## License

MIT — feel free to use, modify, and share!

---

## Contributing

PRs welcome. Feel free to fork and suggest features or fixes!
