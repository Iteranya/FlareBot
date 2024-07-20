import asyncio
import os
import discord
import dotenv
import subprocess
import re
import psutil
import json
from models import *

from discord import app_commands

intents: discord.Intents = discord.Intents.all()
client: discord.Client = discord.Client(command_prefix='/', intents=intents)

async def create_cloudflare_tunnel(tunnel_name, channel: discord.TextChannel):
    # Load the existing tunnel info
    try:
        with open('tunnel_info.json', 'r') as f:
            tunnel_info = json.load(f)
    except FileNotFoundError:
        tunnel_info = {}

    # Find the entry with the same name
    localhost = tunnel_info.get(tunnel_name, {}).get("localhost")
    
    if not localhost:
        await channel.send(f"{tunnel_name}'s tunnel don't exist... Or you made a typo~")
        return None

    cmd = f"cloudflared tunnel -url {localhost}"

    # Start the process
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Pattern to match the Cloudflare URL
    url_pattern = re.compile(r'https?://[a-zA-Z0-9-]+\.trycloudflare\.com')

    # Wait for the URL to appear in the output
    tunnel_created = False
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        line = line.decode('utf-8')
        print(line, end='')  # Print the line for debugging
        match = url_pattern.search(line)
        if match and not tunnel_created:
            cloudflare_url = match.group(0)
            # Store the URL
            if tunnel_name == "Claudia":
                access = cloudflare_url + "/nextcloud"
            else:
                access = cloudflare_url
            tunnel = FlareTunnel(
                name=tunnel_name,
                description = "",
                localhost=localhost,
                flarelink=cloudflare_url,
                accesslink=access
            )
            store_tunnel_info(tunnel)
            await channel.send(f"Tunnel Updated! Check out `/tunnel list` for details~")
            tunnel_created = True

    # Wait for the process to complete in the background
    await process.wait()

    return None

def store_tunnel_info(tunnel: FlareTunnel):
    try:
        with open('tunnel_info.json', 'r') as f:
            tunnel_info = json.load(f)
            
    except FileNotFoundError:
        tunnel_info = {}

    # Check if the tunnel already exists in the data
    if tunnel.name in tunnel_info:
        # Preserve the existing description
        existing_description = tunnel_info[tunnel.name]['description']
        tunnel_info[tunnel.name] = {
            'description': existing_description,
            'localhost': tunnel.localhost,
            'flarelink': tunnel.flarelink,
            'accesslink': tunnel.accesslink
        }
        action = "updated"
    else:
        # Add new tunnel info
        tunnel_info[tunnel.name] = {
            'description': tunnel.description,
            'localhost': tunnel.localhost,
            'flarelink': tunnel.flarelink,
            'accesslink': tunnel.accesslink
        }
        action = "added"

    with open('tunnel_info.json', 'w') as f:
        json.dump(tunnel_info, f, indent=4)  # Added indent for prettier formatting

    # Return a message about what happened
    return f"Tunnel for {tunnel.name} has been {action}."

def show_list():
    try:
        with open('tunnel_info.json', 'r') as f:
            tunnel_info = json.load(f)
    except Exception:
        return "Eh? Why is there no tunnel... Please let Host-kun know!"

    if not tunnel_info:
        return "Eh? Why is there no tunnel... Please let Host-kun know!"

    message = "Okay~ Here's a list of existing tunnels:\n\n"
    for name, details in tunnel_info.items():
        accesslink = details.get("accesslink", "")
        description = details.get("description")
        status = f"Active at {accesslink}" if accesslink else "Inactive"
        message += f"**Name:** {name}\n**Description:** {description}\n**Status:** {status}\n\n"

    message += "If any of these links don't work, use the `/tunnel activate <name>` command. \nIf it also don't work, ping the bot owner!"

    return message

def show_help():
    return """
    Hi! I'm Flare-chan~ Your friendly Reverse Proxy Tunnel Management Bot! 
    Due to the nature of secrecy and anonymity of our services...
    I will be responsible to give you access to them!

    Here are the commands:
    `/tunnel help`: Pull up the friendly instruction I've wrote!
    `/tunnel list`: This command will bring up all the available tunnel access!
    `/tunnel activate`: This command  will activate a tunnel if the link is broken!
    `/tunnel create`: Ah! This command is for Host-kun personal use, please don't use it~
"""


def add_tunnel_entry(name: str, description: str, localhost: str):
    try:
        with open('tunnel_info.json', 'r') as f:
            try:
                tunnel_info = json.load(f)
                if not isinstance(tunnel_info, dict):
                    raise ValueError("JSON content is not a dictionary.")
            except json.JSONDecodeError:
                # Handle cases where JSON is invalid
                tunnel_info = {}
            except ValueError:
                # Handle cases where JSON is not a dictionary
                tunnel_info = {}
    except FileNotFoundError:
        # File does not exist, so initialize with an empty dictionary
        tunnel_info = {}

    if name in tunnel_info:
        return f"Entry for {name} already exists."

    tunnel_info[name] = {
        "description": description,
        "localhost": localhost,
        "flarelink": "",
        "accesslink": ""
    }

    with open('tunnel_info.json', 'w') as f:
        json.dump(tunnel_info, f, indent=4)

    return f"New tunnel entry for {name} at {localhost} has been added."


def clear_links_from_tunnels(filename='tunnel_info.json'):
    try:
        with open(filename, 'r') as f:
            tunnel_info = json.load(f)
    except FileNotFoundError:
        print("No tunnel_info.json file found.")
        return

    # Iterate through each tunnel entry and remove accesslink and flarelink
    for tunnel in tunnel_info.values():
        if 'accesslink' in tunnel:
            del tunnel['accesslink']
        if 'flarelink' in tunnel:
            del tunnel['flarelink']

    with open(filename, 'w') as f:
        json.dump(tunnel_info, f, indent=4)  # Added indent for prettier formatting

    print("Accesslink and flarelink fields have been cleared from all tunnels.")


dotenv.load_dotenv()
discord_token: str | None = os.getenv("DISCORD_TOKEN")
flare_pass: str | None = os.getenv("FLARE_PASS")

def setup_commands():
    group = app_commands.Group(name="tunnel", description=" Commands!!!")

    @group.command(name="help", description="Show Bot Tutorial")
    async def tunnel_help(interaction: discord.Interaction):
        response = show_help()
        await interaction.response.send_message(response, ephemeral=True)

    @group.command(name="list", description="Pull Up A List Of Existing Tunnel")
    async def tunnel_list(interaction: discord.Interaction):
        response = show_list()
        await interaction.response.send_message(response, ephemeral=True)

    @group.command(name="activate", description="Activate or Restart A Tunnel")
    async def tunnel_activate(interaction: discord.Interaction, name:str):
        await interaction.response.send_message("Activating Tunnel~ Please Wait!", ephemeral=True)
        await create_cloudflare_tunnel(name,interaction.channel)

    @group.command(name="create", description="Create A Tunnel")
    async def tunnel_create(interaction: discord.Interaction, name:str, description:str,localhost:str,password:str):
        user_display = interaction.user.display_name
        if password == flare_pass:
            await interaction.response.send_message(
                add_tunnel_entry(name,description,localhost), 
                ephemeral=True)
            
            
        else:
            await interaction.response.send_message(f"Ehh??? Wrong password! Sorry {user_display}, this interaction is for Host only! Sorry~\nBe sure to access `/tunnel help` for list of available command!", ephemeral=True) 
        

    tree.add_command(group)




if discord_token is None:
    raise RuntimeError("$DISCORD_TOKEN env variable is not set!")

client = client

tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    # Let owner known in the console that the bot is now running!
    print(f'Discord Bot is Loading...')

    setup_commands()
    clear_links_from_tunnels()
    await tree.sync(guild=None)
    print(f'Discord Bot is up and running.')


# Run the Bot
client.run(discord_token)