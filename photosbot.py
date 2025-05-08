pimport discord
from discord.ext import commands
from PIL import Image
import piexif
import rawpy
import exifread
from io import BytesIO

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PHOTO_DUMP_CHANNEL = "photo-dump"
PHOTOGRAPHY_CHANNEL = "photography"
PINK = discord.Color.from_str("#FFB6C1")


async def extract_exif_jpeg(image_bytes):
    """Extract EXIF data from JPEG/PNG images."""
    print("Extracting EXIF data from JPEG/PNG image...")
    try:
        img = Image.open(BytesIO(image_bytes))
        exif_dict = piexif.load(img.info.get('exif', b''))
        print("EXIF data extracted successfully.")

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
        print(f"Error extracting EXIF data from JPEG/PNG: {e}")
        return {k: "Unknown" for k in ("Camera Model", "ISO", "Aperture", "Shutter Speed")}


async def extract_exif_cr2(cr2_bytes):
    """Extract EXIF data from CR2 RAW images."""
    print("Extracting EXIF data from CR2 RAW image...")
    try:
        tags = exifread.process_file(BytesIO(cr2_bytes), details=False)
        print("EXIF data extracted successfully.")

        def lookup(name):
            return str(tags.get(name, "Unknown"))

        return {
            "Camera Model": lookup("Image Model"),
            "ISO": lookup("EXIF ISOSpeedRatings"),
            "Aperture": lookup("EXIF FNumber"),
            "Shutter Speed": lookup("EXIF ExposureTime"),
        }
    except Exception as e:
        print(f"Error extracting EXIF data from CR2: {e}")
        return {k: "Unknown" for k in ("Camera Model", "ISO", "Aperture", "Shutter Speed")}


async def parse_manual_fields(content: str):
    """Parse manual overrides from message content."""
    print("Parsing manual fields from message content...")
    data = {}
    for line in content.splitlines():
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key_norm = key.strip().lower()
        if key_norm in ("iso", "aperture", "shutter speed", "camera model", "note"):
            data[key_norm.title()] = val.strip()
    print(f"Parsed manual fields: {data}")
    return data


async def process_attachment(attachment, message):
    """Process a single attachment and return embed and file."""
    print(f"Processing attachment: {attachment.filename}")
    data = await attachment.read()
    filename = attachment.filename
    ext = filename.lower().split('.')[-1]

    if ext in ['jpg', 'jpeg', 'png']:
        print("Detected JPEG/PNG file.")
        exif = await extract_exif_jpeg(data)
        img = Image.open(BytesIO(data))

        file_buffer = BytesIO()
        if len(data) > 8 * 1024 * 1024:
            print("File size exceeds limit, compressing image...")
            img.save(file_buffer, format='JPEG', quality=85)
        else:
            img.save(file_buffer, format=img.format)
        file_buffer.seek(0)

        file_to_send = discord.File(file_buffer, filename=filename)
        image_ref = f"attachment://{filename}"

    elif ext in ['cr2', 'CR2']:
        print("Detected CR2 RAW file.")
        exif = await extract_exif_cr2(data)
        with rawpy.imread(BytesIO(data)) as raw:
            rgb = raw.postprocess()
        img = Image.fromarray(rgb)

        png_buffer = BytesIO()
        if len(data) > 8 * 1024 * 1024:
            print("File size exceeds limit, compressing image...")
            img.save(png_buffer, format='JPEG', quality=85)
            png_buffer.seek(0)
            file_to_send = discord.File(png_buffer, filename="converted.jpg")
            image_ref = "attachment://converted.jpg"
        else:
            img.save(png_buffer, format='PNG')
            png_buffer.seek(0)
            file_to_send = discord.File(png_buffer, filename="converted.png")
            image_ref = "attachment://converted.png"

    else:
        print(f"Unsupported file type: {ext}")
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
    embed.add_field(
        name="📥 Download Original",
        value=f"[Click Here]({attachment.url})",
        inline=False
    )
  
    embed.set_footer(text="Clandestine Cat Cafe • Photography Corner")

    print(f"Generated embed: {embed.to_dict()}")
    return embed, file_to_send


@bot.event
async def on_ready():
    print(f"🎀 Logged in as {bot.user}")


@bot.event
async def on_message(message):
  
    if message.author.bot:
        return

    if message.channel.name != PHOTO_DUMP_CHANNEL:
        return

    if not message.attachments:
        print("No attachments found in the message.")
        return

    photography_channel = discord.utils.get(message.guild.text_channels, name=PHOTOGRAPHY_CHANNEL)
    if not photography_channel:
        print(f"Photography channel '{PHOTOGRAPHY_CHANNEL}' not found.")
        return

    for attachment in message.attachments:
        embed, file_to_send = await process_attachment(attachment, message)
        if embed and file_to_send:
            print(f"Sending processed file and embed to {PHOTOGRAPHY_CHANNEL}.")
            await photography_channel.send(file=file_to_send, embed=embed)

    await bot.process_commands(message)


bot.run("TOKEN")
