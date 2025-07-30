import discord
from discord.ext import commands
from PIL import Image
import piexif
import rawpy
import exifread
import json
from io import BytesIO
import os

# Load settings from settings.json
with open("settings.json") as f:
    config = json.load(f)

BOT_TOKEN = config["BOT_TOKEN"]
PHOTO_DUMP_CHANNEL = config["PHOTO_DUMP_CHANNEL"]
PHOTOGRAPHY_CHANNEL = config["PHOTOGRAPHY_CHANNEL"]
PINK = discord.Color.from_str(config.get("EMBED_COLOR", "#FFB6C1"))
EMBED_FOOTER = config.get("EMBED_FOOTER", "Photography Bot")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def extract_exif_jpeg(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes))
        exif_dict = piexif.load(img.info.get('exif', b''))

        def get(section, tag):
            v = exif_dict.get(section, {}).get(tag)
            if isinstance(v, bytes):
                return v.decode(errors='ignore')
            if isinstance(v, tuple) and len(v) == 2:
                return f"{v[0]}/{v[1]}"
            return str(v) if v else "Unknown"

        return {
            "Camera Model": get("0th", piexif.ImageIFD.Model),
            "ISO": get("Exif", piexif.ExifIFD.ISOSpeedRatings),
            "Aperture": get("Exif", piexif.ExifIFD.FNumber),
            "Shutter Speed": get("Exif", piexif.ExifIFD.ExposureTime),
        }
    except Exception as e:
        print(f"[EXIF-JPEG ERROR] {e}")
        return {k: "Unknown" for k in ("Camera Model", "ISO", "Aperture", "Shutter Speed")}


async def extract_exif_cr2(cr2_bytes):
    try:
        tags = exifread.process_file(BytesIO(cr2_bytes), details=False)

        def lookup(name):
            return str(tags.get(name, "Unknown"))

        return {
            "Camera Model": lookup("Image Model"),
            "ISO": lookup("EXIF ISOSpeedRatings"),
            "Aperture": lookup("EXIF FNumber"),
            "Shutter Speed": lookup("EXIF ExposureTime"),
        }
    except Exception as e:
        print(f"[EXIF-CR2 ERROR] {e}")
        return {k: "Unknown" for k in ("Camera Model", "ISO", "Aperture", "Shutter Speed")}


async def parse_manual_fields(content: str):
    data = {}
    for line in content.splitlines():
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key_norm = key.strip().lower()
        if key_norm in ("iso", "aperture", "shutter speed", "camera model", "note"):
            data[key_norm.title()] = val.strip()
    return data


async def process_attachment(attachment, message):
    data = await attachment.read()
    filename = attachment.filename
    ext = filename.lower().split('.')[-1]

    if ext in ['jpg', 'jpeg', 'png']:
        exif = await extract_exif_jpeg(data)
        img = Image.open(BytesIO(data))

        file_buffer = BytesIO()
        if len(data) > 8 * 1024 * 1024:
            img.save(file_buffer, format='JPEG', quality=85)
        else:
            img.save(file_buffer, format=img.format)
        file_buffer.seek(0)

        file_to_send = discord.File(file_buffer, filename=filename)
        image_ref = f"attachment://{filename}"

    elif ext in ['cr2']:
        exif = await extract_exif_cr2(data)
        with rawpy.imread(BytesIO(data)) as raw:
            rgb = raw.postprocess()
        img = Image.fromarray(rgb)

        buffer = BytesIO()
        if len(data) > 8 * 1024 * 1024:
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            file_to_send = discord.File(buffer, filename="converted.jpg")
            image_ref = "attachment://converted.jpg"
        else:
            img.save(buffer, format='PNG')
            buffer.seek(0)
            file_to_send = discord.File(buffer, filename="converted.png")
            image_ref = "attachment://converted.png"

    else:
        print(f"[SKIP] Unsupported file type: {ext}")
        return None, None

    manual = await parse_manual_fields(message.content)
    for field in ("Camera Model", "ISO", "Aperture", "Shutter Speed"):
        if field in manual:
            exif[field] = manual[field]
    note = manual.get("Note")

    embed = discord.Embed(
        title="📸 New Photo Submission",
        description=f"Uploaded by {message.author.mention} 🐾",
        color=PINK
    )

    embed.set_image(url=image_ref)
    for k, v in exif.items():
        if v and v != "Unknown":
            embed.add_field(name=k, value=v, inline=True)
    if note:
        embed.add_field(name="📝 Note", value=note, inline=False)
    embed.add_field(name="📥 Download Original", value=f"[Click Here]({attachment.url})", inline=False)
    embed.set_footer(text=EMBED_FOOTER)

    return embed, file_to_send


@bot.event
async def on_ready():
    print(f"[READY] Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot or message.channel.name != PHOTO_DUMP_CHANNEL:
        return

    if not message.attachments:
        print("[INFO] No attachments in message.")
        return

    photography_channel = discord.utils.get(message.guild.text_channels, name=PHOTOGRAPHY_CHANNEL)
    if not photography_channel:
        print(f"[ERROR] Channel '{PHOTOGRAPHY_CHANNEL}' not found.")
        return

    for attachment in message.attachments:
        embed, file_to_send = await process_attachment(attachment, message)
        if embed and file_to_send:
            await photography_channel.send(file=file_to_send, embed=embed)

    await bot.process_commands(message)


bot.run(BOT_TOKEN)
