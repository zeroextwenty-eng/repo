"""
multi_bot.py – unified Discord deobfuscator & obfuscator with engine dropdown selector, paste modals, & modern UI embeds.
"""
import asyncio
import io
import logging
import os
import sys
import tempfile
import time

try:
    import aiohttp
    import discord
    from discord import app_commands
except ImportError:
    raise ImportError("discord.py not installed. Run: pip install -r requirements.txt")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENV  = os.path.join(_HERE, ".env")
if os.path.exists(_ENV):
    with open(_ENV) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from deobf_tools import detect_and_run, run_engine, run_veil_obfuscate, ENGINE_RUNNERS, TOOLS  # noqa: E402

log = logging.getLogger("multi_bot")

TOKEN      = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID   = int(os.environ["GUILD_ID"]) if os.environ.get("GUILD_ID") else None
MAX_MB     = float(os.environ.get("MAX_MB", 3))
MAX_BYTES  = int(MAX_MB * 1024 * 1024)
COOLDOWN   = float(os.environ.get("COOLDOWN", 15))
PREFIX     = "!"
SCRIPT_EXT = (".lua", ".luau", ".txt")

# UI Colors
CLR_SUCCESS = 0x57F287  # Soft Green
CLR_PROCESS = 0x5865F2  # Blurple
CLR_ERROR   = 0xED4245  # Red

_last: dict[int, float] = {}

def _check_cooldown(uid: int) -> float:
    t = _last.get(uid, 0)
    rem = COOLDOWN - (time.monotonic() - t)
    return rem if rem > 0 else 0

def _stamp(uid: int):
    _last[uid] = time.monotonic()

def _safe_name(name: str) -> str:
    keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    stem = "".join(c if c in keep else "_" for c in (name or "script"))
    return stem[:60] or "script"

async def _fetch_url(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        if r.status != 200:
            raise ValueError(f"HTTP {r.status} from {url}")
        ct = r.headers.get("content-type", "")
        if "html" in ct:
            raise ValueError("URL returned HTML – paste the raw URL instead.")
        data = await r.read()
        if len(data) > MAX_BYTES:
            raise ValueError(f"File too large (max {MAX_MB:g} MB).")
        return data

def _normalise_url(url: str) -> str:
    import re
    url = re.sub(r"github\.com/([^/]+/[^/]+)/blob/", r"raw.githubusercontent.com/\1/", url)
    url = re.sub(r"pastebin\.com/(?!raw/)([A-Za-z0-9]+)$", r"pastebin.com/raw/\1", url)
    url = re.sub(r"gist\.github\.com/([^/]+/[a-f0-9]+)$", r"gist.githubusercontent.com/\1/raw", url)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def _extract_url(text: str) -> str | None:
    import re
    m = re.search(r'https?://\S+', text or "")
    return m.group(0).rstrip(")'\"") if m else None

async def _execute_deobf(data: bytes, stem: str, engine: str = "auto") -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()
    def _work():
        with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, prefix="mbot_in_") as tf:
            tf.write(data)
            path = tf.name
        try:
            text, label = run_engine(engine, path)
            return text, label
        finally:
            try: os.unlink(path)
            except OSError: pass

    text, label = await loop.run_in_executor(None, _work)
    out_name = _safe_name(stem) + "_deobf.lua"
    return text, out_name, label

async def _execute_obf(data: bytes, stem: str, preset: str = "heavy") -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()
    def _work():
        with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, prefix="mbot_obf_") as tf:
            tf.write(data)
            path = tf.name
        try:
            text, label = run_veil_obfuscate(path, preset)
            return text, label
        finally:
            try: os.unlink(path)
            except OSError: pass

    text, label = await loop.run_in_executor(None, _work)
    out_name = _safe_name(stem) + "_obf.lua"
    return text, out_name, label


ENGINE_OPTIONS = [
    discord.SelectOption(label="Prometheus / WeAreDevs", value="prometheus", description="Prometheus & WeAreDevs static deobfuscator", emoji="🔥", default=True),
    discord.SelectOption(label="Bacon Guard / FORGE", value="baconguard", description="Bacon Guard / FORGE VM", emoji="🥓"),
    discord.SelectOption(label="Centurion (v6 / v6.1)", value="centurion", description="Centurion polymorphic deobfuscator", emoji="🏛️"),
    discord.SelectOption(label="LuaGuard Unpack", value="luaguard", description="Lua-Guard unpacker & structure lifter", emoji="🔓"),
    discord.SelectOption(label="Luraph v15.1", value="luraph_v15_1", description="Latest Luraph v15 devirtualizer", emoji="🛡️"),
    discord.SelectOption(label="Hercules (1.6 - 2.0)", value="hercules", description="Hercules static deobfuscator", emoji="⚔️"),
    discord.SelectOption(label="Clyde (V2 - V6)", value="clyde", description="Clyde stack & register VM", emoji="👻"),
    discord.SelectOption(label="LuaObfuscator", value="luaobfuscator", description="Static LuaObfuscator deobfuscator", emoji="🌀"),
    discord.SelectOption(label="IronBrew2", value="ironbrew2", description="IronBrew2 native lifter", emoji="🍺"),
    discord.SelectOption(label="Ironveil V1", value="ironveil", description="Ironveil V1 deobfuscator", emoji="⛓️"),
    discord.SelectOption(label="77fuscator", value="77fuscator", description="77fuscator static deobfuscator", emoji="💎"),
    discord.SelectOption(label="Luraph / IronBrew1", value="luraph_ironbrew1", description="Luau sandbox runtime lifter", emoji="📦"),
]


# ── Modals & Views ────────────────────────────────────────────────────────────

class PasteCodeModal(discord.ui.Modal, title="Deobfuscate Lua Code"):
    def __init__(self, engine: str = "auto"):
        super().__init__()
        self.engine = engine

    code_input = discord.ui.TextInput(
        label="Obfuscated Lua Code",
        style=discord.TextStyle.paragraph,
        placeholder="Paste your Lua script here…",
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        data = self.code_input.value.encode("utf-8")
        stem = "pasted_script"
        t0 = time.monotonic()
        try:
            text, out_name, label = await asyncio.wait_for(_execute_deobf(data, stem, self.engine), timeout=180)
            elapsed = time.monotonic() - t0
            body = text.encode("utf-8")

            embed = discord.Embed(
                title="✨ Deobfuscation Complete",
                color=CLR_SUCCESS,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="⚙️ Engine", value=f"`{label}`", inline=True)
            embed.add_field(name="⏱️ Duration", value=f"`{elapsed:.2f}s`", inline=True)
            embed.add_field(name="📁 Output Size", value=f"`{len(body)/1024:.1f} KB`", inline=True)
            embed.set_footer(text="Deobfuscated successfully")

            att = discord.File(io.BytesIO(body), filename=out_name)
            await interaction.followup.send(embed=embed, file=att)
        except Exception as e:
            err = discord.Embed(
                title="❌ Deobfuscation Failed",
                description=f"```\n{str(e)[:1500]}\n```",
                color=CLR_ERROR
            )
            await interaction.followup.send(embed=err)


class PasteCodeButton(discord.ui.Button):
    def __init__(self, engine: str = "auto"):
        super().__init__(label="Paste Code", emoji="📝", style=discord.ButtonStyle.primary)
        self.engine = engine

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PasteCodeModal(engine=self.engine))


class EmptyEngineSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select engine to use…",
            min_values=1,
            max_values=1,
            options=ENGINE_OPTIONS
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        label = dict((o.value, o.label) for o in self.options).get(selected, selected)

        embed = discord.Embed(
            title="⚡ Lua Deobfuscator",
            description=f"Selected Engine: **{label}**\n\nClick **Paste Code** below to enter your script, or reply to this message with an attached `.lua` file!",
            color=CLR_PROCESS
        )
        view = discord.ui.View(timeout=180)
        view.add_item(EmptyEngineSelect())
        view.add_item(PasteCodeButton(engine=selected))
        await interaction.response.edit_message(embed=embed, view=view)


class InitialMenuSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(EmptyEngineSelect())
        self.add_item(PasteCodeButton(engine="prometheus"))


class FileEngineSelect(discord.ui.Select):
    def __init__(self, data: bytes, stem: str):
        self.data = data
        self.stem = stem
        super().__init__(placeholder="Choose deobfuscator engine…", min_values=1, max_values=1, options=ENGINE_OPTIONS)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        label = dict((o.value, o.label) for o in self.options).get(selected, selected)

        await interaction.response.defer()
        t0 = time.monotonic()

        proc_embed = discord.Embed(
            title="⚙️ Deobfuscating…",
            description=f"Running **{label}** on `{self.stem}.lua`",
            color=CLR_PROCESS
        )
        await interaction.edit_original_response(embed=proc_embed, view=None)

        try:
            text, out_name, out_label = await asyncio.wait_for(_execute_deobf(self.data, self.stem, selected), timeout=180)
            elapsed = time.monotonic() - t0
            body = text.encode("utf-8")

            success_embed = discord.Embed(
                title="✨ Deobfuscation Complete",
                color=CLR_SUCCESS,
                timestamp=discord.utils.utcnow()
            )
            success_embed.add_field(name="⚙️ Engine", value=f"`{out_label}`", inline=True)
            success_embed.add_field(name="⏱️ Duration", value=f"`{elapsed:.2f}s`", inline=True)
            success_embed.add_field(name="📁 Output Size", value=f"`{len(body)/1024:.1f} KB`", inline=True)
            success_embed.set_footer(text="Deobfuscated successfully")

            att = discord.File(io.BytesIO(body), filename=out_name)
            await interaction.edit_original_response(embed=success_embed, attachments=[att])
        except Exception as e:
            err_embed = discord.Embed(
                title="❌ Deobfuscation Failed",
                description=f"```\n{str(e)[:1500]}\n```",
                color=CLR_ERROR
            )
            await interaction.edit_original_response(embed=err_embed)


class FileEngineSelectView(discord.ui.View):
    def __init__(self, data: bytes, stem: str):
        super().__init__(timeout=180)
        self.add_item(FileEngineSelect(data, stem))


# ── Discord Client ────────────────────────────────────────────────────────────

class MultiDeobfClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._session: aiohttp.ClientSession | None = None

    async def setup_hook(self):
        @self.tree.command(name="deobf", description="Deobfuscate a Lua/Luau script")
        @app_commands.describe(
            file="Attach a .lua / .luau / .txt file",
            url="Or paste a raw link to the script",
            engine="Select the deobfuscation engine"
        )
        @app_commands.choices(engine=[
            app_commands.Choice(name="🔥 Prometheus / WeAreDevs", value="prometheus"),
            app_commands.Choice(name="🥓 Bacon Guard / FORGE", value="baconguard"),
            app_commands.Choice(name="🏛️ Centurion (v6 / v6.1)", value="centurion"),
            app_commands.Choice(name="🔓 LuaGuard Unpack", value="luaguard"),
            app_commands.Choice(name="🛡️ Luraph v15.1", value="luraph_v15_1"),
            app_commands.Choice(name="⚔️ Hercules (1.6 - 2.0)", value="hercules"),
            app_commands.Choice(name="👻 Clyde (V2 - V6)", value="clyde"),
            app_commands.Choice(name="🌀 LuaObfuscator", value="luaobfuscator"),
            app_commands.Choice(name="🍺 IronBrew2", value="ironbrew2"),
            app_commands.Choice(name="⛓️ Ironveil V1", value="ironveil"),
            app_commands.Choice(name="💎 77fuscator", value="77fuscator"),
            app_commands.Choice(name="📦 Luraph / IronBrew1", value="luraph_ironbrew1"),
        ])
        async def slash_deobf(interaction: discord.Interaction,
                               file: discord.Attachment | None = None,
                               url: str | None = None,
                               engine: app_commands.Choice[str] | None = None):
            engine_val = engine.value if engine else "prometheus"
            if file is None and url is None:
                await interaction.response.send_modal(PasteCodeModal(engine=engine_val))
                return
            await self._handle_slash_deobf(interaction, file, url, engine_val)

        @self.tree.command(name="obfuscate", description="Obfuscate a Lua script with Veil")
        @app_commands.describe(
            file="Attach a .lua / .luau / .txt file",
            url="Or paste a raw link to the script",
            preset="Protection intensity"
        )
        @app_commands.choices(preset=[
            app_commands.Choice(name="🟢 Light (Rename + Encrypt Strings)", value="light"),
            app_commands.Choice(name="🟡 Medium (Member & Number Obfuscation)", value="medium"),
            app_commands.Choice(name="🔴 Heavy (Control Flow Flattening)", value="heavy"),
            app_commands.Choice(name="🟣 Maximum (Full VM Wrapper)", value="maximum"),
        ])
        async def slash_obfuscate(interaction: discord.Interaction,
                                   file: discord.Attachment | None = None,
                                   url: str | None = None,
                                   preset: app_commands.Choice[str] | None = None):
            p_val = preset.value if preset else "heavy"
            await self._handle_slash_obf(interaction, file, url, p_val)



        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        log.info("ready: %s (id %s), %d servers", self.user, self.user.id, len(self.guilds))

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
        await super().close()

    async def on_message(self, message: discord.Message):
        pass

    async def _handle_slash_deobf(self, interaction: discord.Interaction,
                                   att: discord.Attachment | None,
                                   url: str | None,
                                   engine: str):
        uid = interaction.user.id
        rem = _check_cooldown(uid)
        if rem:
            await interaction.response.send_message(f"⏳ Please wait {rem:.0f}s.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        data, stem = await self._extract_slash_input(interaction, att, url)
        if not data:
            return

        _stamp(uid)
        t0 = time.monotonic()

        try:
            text, out_name, label = await asyncio.wait_for(_execute_deobf(data, stem, engine), timeout=180)
            body = text.encode("utf-8")
            elapsed = time.monotonic() - t0

            embed = discord.Embed(title="✨ Deobfuscation Complete", color=CLR_SUCCESS, timestamp=discord.utils.utcnow())
            embed.add_field(name="⚙️ Engine", value=f"`{label}`", inline=True)
            embed.add_field(name="⏱️ Duration", value=f"`{elapsed:.2f}s`", inline=True)
            embed.add_field(name="📁 Output Size", value=f"`{len(body)/1024:.1f} KB`", inline=True)
            embed.set_footer(text="Deobfuscated successfully")

            att_file = discord.File(io.BytesIO(body), filename=out_name)
            await interaction.followup.send(embed=embed, file=att_file)
        except Exception as e:
            err = discord.Embed(title="❌ Deobfuscation Failed", description=f"```\n{str(e)[:1500]}\n```", color=CLR_ERROR)
            await interaction.followup.send(embed=err)

    async def _handle_slash_obf(self, interaction: discord.Interaction,
                                 att: discord.Attachment | None,
                                 url: str | None,
                                 preset: str):
        uid = interaction.user.id
        rem = _check_cooldown(uid)
        if rem:
            await interaction.response.send_message(f"⏳ Please wait {rem:.0f}s.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        data, stem = await self._extract_slash_input(interaction, att, url)
        if not data:
            return

        _stamp(uid)
        t0 = time.monotonic()

        try:
            text, out_name, label = await asyncio.wait_for(_execute_obf(data, stem, preset), timeout=60)
            body = text.encode("utf-8")
            elapsed = time.monotonic() - t0

            embed = discord.Embed(title="🔒 Obfuscation Complete", color=CLR_SUCCESS, timestamp=discord.utils.utcnow())
            embed.add_field(name="⚙️ Engine", value=f"`{label}`", inline=True)
            embed.add_field(name="⏱️ Duration", value=f"`{elapsed:.2f}s`", inline=True)
            embed.add_field(name="📁 Output Size", value=f"`{len(body)/1024:.1f} KB`", inline=True)
            embed.set_footer(text="Obfuscated with Veil")

            att_file = discord.File(io.BytesIO(body), filename=out_name)
            await interaction.followup.send(embed=embed, file=att_file)
        except Exception as e:
            err = discord.Embed(title="❌ Obfuscation Failed", description=f"```\n{str(e)[:1500]}\n```", color=CLR_ERROR)
            await interaction.followup.send(embed=err)

    async def _extract_slash_input(self, interaction: discord.Interaction,
                                   att: discord.Attachment | None,
                                   url: str | None) -> tuple[bytes | None, str]:
        if att is not None:
            if not att.filename.lower().endswith(SCRIPT_EXT):
                await interaction.followup.send(f"Only {'/'.join(SCRIPT_EXT)} files supported.", ephemeral=True)
                return None, "script"
            if att.size > MAX_BYTES:
                await interaction.followup.send(f"File too large (max {MAX_MB:g} MB).", ephemeral=True)
                return None, "script"
            return await att.read(), _safe_name(att.filename.rsplit(".", 1)[0])

        if url:
            url = _normalise_url(url)
            try:
                session = await self._get_session()
                data = await _fetch_url(session, url)
                stem = _safe_name(url.rstrip("/").rsplit("/", 1)[-1].rsplit(".", 1)[0] or "script")
                return data, stem
            except Exception as e:
                await interaction.followup.send(f"❌ Could not fetch URL: {e}", ephemeral=True)
                return None, "script"

        await interaction.followup.send("Attach a file or supply a URL.", ephemeral=True)
        return None, "script"

    async def _resolve_source(self, message: discord.Message, prefix_cmd: str) -> tuple[bytes | None, str]:
        for att in message.attachments:
            if att.filename.lower().endswith(SCRIPT_EXT):
                return await att.read(), _safe_name(att.filename.rsplit(".", 1)[0])

        after = message.content.strip()[len(prefix_cmd):].strip()
        url = _extract_url(after) or _extract_url(message.content)
        if url:
            try:
                session = await self._get_session()
                data = await _fetch_url(session, _normalise_url(url))
                stem = _safe_name(url.rstrip("/").rsplit("/", 1)[-1].rsplit(".", 1)[0] or "script")
                return data, stem
            except Exception:
                return None, "script"

        ref = message.reference
        if ref:
            try:
                target = ref.resolved or await message.channel.fetch_message(ref.message_id)
                for att in target.attachments:
                    if att.filename.lower().endswith(SCRIPT_EXT):
                        return await att.read(), _safe_name(att.filename.rsplit(".", 1)[0])
                url2 = _extract_url(target.content)
                if url2:
                    session = await self._get_session()
                    data = await _fetch_url(session, _normalise_url(url2))
                    return data, "script"
            except Exception:
                pass

        return None, "script"


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not TOKEN:
        print("DISCORD_TOKEN not set in .env", file=sys.stderr)
        return 1
    client = MultiDeobfClient()
    try:
        client.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("Discord rejected the token.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
