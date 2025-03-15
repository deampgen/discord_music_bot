import os
import logging
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from discord.utils import get


logging.basicConfig(level=logging.INFO)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


bot = commands.Bot(command_prefix='!', intents=intents)

TRACKS_FOLDER = ""


available_tracks = []


queue = []


def update_available_tracks():
    global available_tracks
    available_tracks = [f for f in os.listdir(TRACKS_FOLDER) if os.path.isfile(os.path.join(TRACKS_FOLDER, f))]
    logging.info(f"Available tracks updated: {available_tracks}")


update_available_tracks()


def find_track_by_substring(substring):
    matching_tracks = [track for track in available_tracks if substring.lower() in track.lower()]
    return matching_tracks


def paginate(text: str, page_length: int = 2000):
    """Функция для разделения текста на страницы."""
    pages = [text[i:i + page_length] for i in range(0, len(text), page_length)]
    return pages


def add_to_queue(track_name):
    matching_tracks = find_track_by_substring(track_name)
    if not matching_tracks:
        return False
    elif len(matching_tracks) > 1:
        return False
    queue.append(matching_tracks[0])
    return True


def play_next_track(ctx):
    if queue:
        next_track = queue.pop(0)
        track_path = os.path.join(TRACKS_FOLDER, next_track)
        ctx.voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=track_path), after=lambda e: logging.error('Player error: %s', e) if e else play_next_track(ctx))
        return next_track
    return None


@bot.command(name='music')
async def play_music(ctx, *, track_name: str):
    """
    Воспроизводит указанный трек в канале пользователя.
    Использование: !music <track_name>
    """
    logging.info(f"Received command: {ctx.command.name}, args: {track_name}")

    
    if ctx.author.voice is None:
        await ctx.send("Вы не подключены к голосовому каналу.")
        return

    voice_channel = ctx.author.voice.channel

    
    if ctx.voice_client is None:
        
        voice_client = await voice_channel.connect()
    else:
        voice_client = ctx.voice_client
        if voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

    if add_to_queue(track_name):
        await ctx.send(f"Трек `{track_name}` добавлен в очередь.")
    else:
        await ctx.send(f"Трек `{track_name}` не найден.\nДоступные треки:\n{', '.join(available_tracks)}")

    if not voice_client.is_playing():
        play_next_track(ctx)


@bot.command(name='pause')
async def pause_music(ctx):
    """
    Приостанавливает воспроизведение текущего трека.
    Использование: !pause
    """
    if ctx.voice_client is not None:
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Текущий трек приостановлен.")
        else:
            await ctx.send("Ничего не воспроизводится.")
    else:
        await ctx.send("Я не подключен к голосовому каналу.")


@bot.command(name='resume')
async def resume_music(ctx):
    """
    Возобновляет воспроизведение текущего трека.
    Использование: !resume
    """
    if ctx.voice_client is not None:
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Текущий трек возобновлен.")
        else:
            await ctx.send("Текущий трек не приостановлен.")
    else:
        await ctx.send("Я не подключен к голосовому каналу.")


@bot.command(name='tracks')
async def list_tracks(ctx):
    """
    Отправляет список всех доступных треков.
    Использование: !tracks
    """
    if not available_tracks:
        await ctx.send("Список треков пуст.")
        return

    
    pages = paginate(f"Доступные треки:\n{''.join([f'{track}\n' for track in available_tracks])}")

    for page in pages:
        await ctx.send(page)


@bot.command(name='update_tracks')
async def update_tracks_list(ctx):
    """
    Обновляет список доступных треков.
    Использование: !update_tracks
    """
    update_available_tracks()
    await ctx.send("Список треков обновлен.")


@bot.command(name='stop')
async def stop_music(ctx):
    """
    Останавливает воспроизведение и отключает бота от голосового канала.
    Использование: !stop
    """
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send("Отключился от голосового канала.")
    else:
        await ctx.send("Я не подключен к голосовому каналу.")


@bot.command(name='add')
async def add_to_queue_command(ctx, *, track_name: str):
    """
    Добавляет трек в очередь воспроизведения.
    Использование: !add <track_name>
    """
    if add_to_queue(track_name):
        await ctx.send(f"Трек `{track_name}` добавлен в очередь.")
    else:
        await ctx.send(f"Трек `{track_name}` не найден.\nДоступные треки:\n{', '.join(available_tracks)}")

# Команда для получения текущего трека
@bot.command(name='current')
async def current_track(ctx):
    """
    Отправляет текущий трек.
    Использование: !current
    """
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send(f"Текущий трек: `{ctx.voice_client.source.title}`")
    else:
        await ctx.send("Ничего не воспроизводится.")

# Команда для получения очереди треков
@bot.command(name='queue')
async def show_queue(ctx):
    """
    Отправляет текущую очередь треков.
    Использование: !queue
    """
    if not queue:
        await ctx.send("Очередь треков пуста.")
        return

    await ctx.send(f"Очередь треков:\n{', '.join(queue)}")

class MusicControls(View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    @discord.ui.button(label="Пауза", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            await interaction.response.send_message("Текущий трек приостановлен.", ephemeral=True)
        else:
            await interaction.response.send_message("Ничего не воспроизводится.", ephemeral=True)

    @discord.ui.button(label="Продолжить", style=discord.ButtonStyle.green)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
            await interaction.response.send_message("Текущий трек возобновлен.", ephemeral=True)
        else:
            await interaction.response.send_message("Текущий трек не приостановлен.", ephemeral=True)

    @discord.ui.button(label="Следующий", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()
            await interaction.response.send_message("Переход к следующему треку.", ephemeral=True)
        else:
            await interaction.response.send_message("Ничего не воспроизводится.", ephemeral=True)


@bot.command(name='controls')
async def show_controls(ctx):
    """
    Отправляет кнопки управления воспроизведением.
    Использование: !controls
    """
    view = MusicControls(ctx)
    await ctx.send("Контроли воспроизведения:", view=view)


bot.run('')
