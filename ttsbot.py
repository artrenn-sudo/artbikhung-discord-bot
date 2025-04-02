import discord
import os
import random
from discord.ext import commands
from discord.ui import View, Button 
import asyncio
import openai
import requests
from gtts import gTTS
from discord import FFmpegPCMAudio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

rps_games = {}

@bot.event
async def on_ready():
    print(f"{bot.user} đang online!")
    await bot.tree.sync()
    print("Bot is ready and commands are synchronized.")

@bot.tree.command(name="menu", description="Show game command menu")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message("""
🎮 **Game Menu:**
- `/roll_dice [sides]` or `mtdr` — Roll a dice (default 6 sides)
- `/flip_coin` or `mtfc` — Flip a coin
- `/rps choice:` or `mtrps rock/paper/scissors` — Rock, Paper, Scissors vs bot
- `/rps_challenge @user` or `mtrpsu @user` — Challenge a user
- `/rps_play choice:` or `mtrpsu rock/paper/scissors` — Make your move
""")

# 🎲 Dice Roll with Buttons
@bot.tree.command(name="roll_dice", description="Roll a 6-sided dice with button.")
async def roll_dice(interaction: discord.Interaction):
    class DiceView(View):
        @discord.ui.button(label="Roll 🎲", style=discord.ButtonStyle.primary)
        async def roll(self, button: Button, inter: discord.Interaction):
            result = random.randint(1, 6)
            await inter.response.edit_message(content=f"🎲 You rolled a **{result}**!", view=self)

    await interaction.response.send_message("Click the button to roll the dice!", view=DiceView())

# 🪙 Coin Flip with Buttons
@bot.tree.command(name="flip_coin", description="Flip a coin with button.")
async def flip_coin(interaction: discord.Interaction):
    class CoinView(View):
        @discord.ui.button(label="Flip 🪙", style=discord.ButtonStyle.secondary)
        async def flip(self, button: Button, inter: discord.Interaction):
            result = random.choice(["Heads", "Tails"])
            await inter.response.edit_message(content=f"🪙 The coin landed on **{result}**!", view=self)

    await interaction.response.send_message("Click the button to flip a coin!", view=CoinView())

# 🤖 Rock, Paper, Scissors vs Bot
@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors vs the bot.")
async def rps(interaction: discord.Interaction):
    class RPSView(View):
        @discord.ui.button(label="Rock 🪨", style=discord.ButtonStyle.primary)
        async def rock(self, button: Button, inter: discord.Interaction):
            await self.play(inter, "rock")

        @discord.ui.button(label="Paper 📄", style=discord.ButtonStyle.success)
        async def paper(self, button: Button, inter: discord.Interaction):
            await self.play(inter, "paper")

        @discord.ui.button(label="Scissors ✂️", style=discord.ButtonStyle.danger)
        async def scissors(self, button: Button, inter: discord.Interaction):
            await self.play(inter, "scissors")

        async def play(self, inter: discord.Interaction, user_choice: str):
            bot_choice = random.choice(["rock", "paper", "scissors"])
            result = ""
            if user_choice == bot_choice:
                result = "It's a tie!"
            elif (user_choice == "rock" and bot_choice == "scissors") or \
                 (user_choice == "scissors" and bot_choice == "paper") or \
                 (user_choice == "paper" and bot_choice == "rock"):
                result = "You win!"
            else:
                result = "You lose!"
            await inter.response.edit_message(content=f"You chose **{user_choice}**, I chose **{bot_choice}**. {result}", view=self)

    await interaction.response.send_message("Choose your move:", view=RPSView())

@bot.tree.command(name="rps_challenge", description="Challenge another user to Rock, Paper, Scissors!")
async def rps_challenge(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.bot:
        await interaction.response.send_message("You can't challenge a bot!")
        return

    rps_games[interaction.user.id] = {"opponent": opponent.id, "choice": None}
    rps_games[opponent.id] = {"opponent": interaction.user.id, "choice": None}

    await interaction.response.send_message(
        f"{opponent.mention}, you've been challenged by {interaction.user.mention} to a game of Rock, Paper, Scissors!\n"
        f"Both players must use `/rps_play choice:` to play!"
    )

@bot.tree.command(name="rps_play", description="Play your move in Rock, Paper, Scissors.")
async def rps_play(interaction: discord.Interaction, choice: str):
    user_id = interaction.user.id
    valid_choices = ["rock", "paper", "scissors"]
    choice = choice.lower()

    if choice not in valid_choices:
        await interaction.response.send_message("Invalid choice. Use rock, paper, or scissors.")
        return

    if user_id not in rps_games:
        await interaction.response.send_message("You are not currently in a game.")
        return

    game = rps_games[user_id]
    opponent_id = game["opponent"]

    rps_games[user_id]["choice"] = choice

    if opponent_id in rps_games and rps_games[opponent_id]["choice"]:
        opponent_choice = rps_games[opponent_id]["choice"]
        user_choice = rps_games[user_id]["choice"]

        if user_choice == opponent_choice:
            result = "It's a tie!"
        elif (user_choice == "rock" and opponent_choice == "scissors") or \
             (user_choice == "scissors" and opponent_choice == "paper") or \
             (user_choice == "paper" and opponent_choice == "rock"):
            result = f"{interaction.user.mention} wins!"
        else:
            result = f"<@{opponent_id}> wins!"

        await interaction.response.send_message(
            f"You played **{user_choice}**, <@{opponent_id}> played **{opponent_choice}**.\n{result}"
        )

        del rps_games[user_id]
        del rps_games[opponent_id]
    else:
        await interaction.response.send_message("Your move has been recorded. Waiting for your opponent to play.")

# 🧠 Tic-Tac-Toe PvP Game
@bot.tree.command(name="tictactoe", description="Start a Tic-Tac-Toe game with another user.")
async def tictactoe(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.bot or opponent == interaction.user:
        await interaction.response.send_message("You must challenge a human opponent!")
        return

    board = ["⬜"] * 9
    current_turn = interaction.user
    ttt_games[interaction.channel.id] = {
        "board": board,
        "players": [interaction.user, opponent],
        "turn": current_turn
    }

    await interaction.response.send_message(
        f"🎮 Tic-Tac-Toe between {interaction.user.mention} and {opponent.mention}! {current_turn.mention}'s turn.",
        view=TicTacToeView(interaction.channel.id)
    )

class TicTacToeView(View):
    def __init__(self, channel_id):
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        board = ttt_games[self.channel_id]["board"]
        for i in range(9):
            emoji = board[i]
            row = i // 3
            col = i % 3
            style = discord.ButtonStyle.secondary
            self.add_item(TTTButton(label=emoji, row=row, index=i, style=style))

class TTTButton(Button):
    def __init__(self, label, row, index, style):
        super().__init__(label=label, row=row, style=style, custom_id=str(index))
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        game = ttt_games.get(interaction.channel.id)
        if not game:
            await interaction.response.send_message("This game has expired.", ephemeral=True)
            return

        board = game["board"]
        current_turn = game["turn"]
        players = game["players"]

        if interaction.user != current_turn:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if board[self.index] != "⬜":
            await interaction.response.send_message("That spot is already taken!", ephemeral=True)
            return

        mark = "❌" if current_turn == players[0] else "⭕"
        board[self.index] = mark

        winner = check_ttt_winner(board)
        game["turn"] = players[1] if current_turn == players[0] else players[0]

        view = TicTacToeView(interaction.channel.id)
        if winner:
            del ttt_games[interaction.channel.id]
            await interaction.response.edit_message(content=f"🏆 {interaction.user.mention} wins!", view=view)
        elif "⬜" not in board:
            del ttt_games[interaction.channel.id]
            await interaction.response.edit_message(content="It's a draw!", view=view)
        else:
            await interaction.response.edit_message(content=f"{game['turn'].mention}'s turn.", view=view)

def check_ttt_winner(board):
    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for a, b, c in wins:
        if board[a] == board[b] == board[c] and board[a] != "⬜":
            return True

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    if content.startswith("mtdr"):
        result = random.randint(1, 6)
        await message.channel.send(f"🎲 You rolled a {result}!")

    elif content.startswith("mtfc"):
        result = random.choice(["Heads", "Tails"])
        await message.channel.send(f"🪙 The coin landed on: **{result}**")

    elif content.startswith("mtrps"):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("Please specify your move: rock, paper, or scissors.")
            return
        user_choice = parts[1]
        valid_choices = ["rock", "paper", "scissors"]
        if user_choice not in valid_choices:
            await message.channel.send("Invalid choice. Use rock, paper, or scissors.")
            return
        bot_choice = random.choice(valid_choices)
        if user_choice == bot_choice:
            result = "It's a tie!"
        elif (user_choice == "rock" and bot_choice == "scissors") or \
             (user_choice == "scissors" and bot_choice == "paper") or \
             (user_choice == "paper" and bot_choice == "rock"):
            result = "You win!"
        else:
            result = "You lose!"
        await message.channel.send(f"You chose **{user_choice}**, I chose **{bot_choice}**. {result}")

    elif content.startswith("mtrpsu"):
        await message.channel.send("Use `/rps_challenge @user` to start a PvP game!")

    await bot.process_commands(message)

@bot.tree.command(name="ask", description="Ask the bot anything!")
async def ask(interaction: discord.Interaction, *, question: str):
    await interaction.response.defer()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}]
        )

        answer = response['choices'][0]['message']['content']
        await interaction.followup.send(answer)

    except Exception as e:
        await interaction.followup.send("An error occurred while fetching a response.")
        print(f"Error: {e}")

@bot.tree.command(name="generate_image", description="Generate an image based on a prompt.")
async def generate_image(interaction: discord.Interaction, *, prompt: str):
    await interaction.response.defer()

    try:
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

        image_url = response['data'][0]['url']
        image_data = requests.get(image_url).content
        image_path = "generated_image.png"

        with open(image_path, "wb") as f:
            f.write(image_data)

        await interaction.followup.send(file=discord.File(image_path))

    except Exception as e:
        await interaction.followup.send("Failed to generate an image.")
        print(f"Error: {e}")

@bot.tree.command(name="upload_file", description="Generate and upload a file with custom content.")
async def upload_file(interaction: discord.Interaction, *, content: str = "This is a sample file generated by the bot."):
    await interaction.response.defer()

    file_path = "generated_file.txt"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        await interaction.followup.send("Here is your generated file:", file=discord.File(file_path))

    except Exception as e:
        await interaction.followup.send("Failed to generate the file.")
        print(f"Error: {e}")

from fpdf import FPDF

@bot.tree.command(name="upload_pdf", description="Generate and upload a PDF file.")
async def upload_pdf(interaction: discord.Interaction, *, content: str = "This is a sample PDF file."):
    await interaction.response.defer()

    file_path = "generated_file.pdf"
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.output(file_path)

        await interaction.followup.send("Here is your generated PDF:", file=discord.File(file_path))

    except Exception as e:
        await interaction.followup.send("Failed to generate the PDF.")
        print(f"Error: {e}")

# TTS greeting
@bot.event
async def on_voice_state_update(member, before, after):
    """ The bot only greets if it's already in a voice channel """
    bot_voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

    if bot_voice_client and after.channel == bot_voice_client.channel:
        try:
            await asyncio.sleep(1)

            text_to_speak = f"Xin chào {member.name}"
            tts = gTTS(text=text_to_speak, lang="vi")  # Vietnamese
            temp_audio_name = "greeting.mp3"
            tts.save(temp_audio_name)

            FFMPEG_PATH = "C:/Users/as/ffmpeg/bin/ffmpeg"

            if bot_voice_client.is_playing():
                while bot_voice_client.is_playing():
                    await asyncio.sleep(0.5)

            bot_voice_client.play(
                FFmpegPCMAudio(temp_audio_name, executable=FFMPEG_PATH),
                after=lambda e: print("Greeting audio finished")
            )
            print(f"🎤 Greeting audio played for {member.name}")
        except Exception as e:
            print(f"Error playing greeting audio: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    language_codes = {
        "en": "English",
        "es": "Spanish",
        "ko": "Korean",
        "zh": "Mandarin",
        "vi": "Vietnamese"
    }

    # Check if message starts with "mt" for text-to-speech
    if message.content.lower().startswith("mt"):
        bot_voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)

        # Ensure the bot is already in a voice channel
        if bot_voice_client and message.author.voice and message.author.voice.channel == bot_voice_client.channel:
            try:
                parts = message.content.split(" ", 2)  # Split command into parts
                if len(parts) > 2 and parts[1] in language_codes:
                    lang = parts[1]  # Language code
                    text_to_read = parts[2]  # Message content
                else:
                    lang = "vi"  # Default to Vietnamese
                    text_to_read = message.content[3:].strip()

                tts = gTTS(text=text_to_read, lang=lang)
                temp_audio_name = "message.mp3"
                tts.save(temp_audio_name)

                FFMPEG_PATH = "C:/Users/as/ffmpeg/bin/ffmpeg"

                if bot_voice_client.is_playing():
                    while bot_voice_client.is_playing():
                        await asyncio.sleep(0.5)
                
                # Play audio
                bot_voice_client.play(
                    FFmpegPCMAudio(temp_audio_name, executable=FFMPEG_PATH),
                    after=lambda e: print("TTS message audio finished")
                )

                print(f"🎤 {message.author.name} in #{message.channel.name} ({message.guild.name}) - {language_codes[lang]}: {text_to_read}")
            except Exception as e:
                print(f"Error generating TTS audio: {e}")
        else:
            print(f"❌ {message.author.name} tried to use TTS but is not in the same voice channel as the bot.")

    await bot.process_commands(message)

bot.run(TOKEN)
