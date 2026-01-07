import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import json, os, traceback

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DATA_FILE = "data.json"
VN_TZ = timezone(timedelta(hours=7))
DEADLINE_DAYS = 7

# ================= THEME =================
COLOR = {1: 0xFF6B6B, 2: 0xFF4757, 3: 0xC0392B}
FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"

PENALTY = {
    1: "⚠️ Cảnh cáo",
    2: "💰 Đóng quỹ 500.000",
    3: "💸 Đóng quỹ 1.000.000",
    5: "👢 Kick crew",
    7: "⛔ Ban vĩnh viễn"
}

# ================= BOT =================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA =================
DEFAULT_DATA = {
    "config": {"log_channel": None},
    "case_id": 0,
    "users": {}
}

def load():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DATA, f, indent=2, ensure_ascii=False)
        return DEFAULT_DATA.copy()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load()

# ================= UTILS =================
def is_admin(m: discord.Member):
    return m.guild_permissions.administrator

def next_case():
    data["case_id"] += 1
    save()
    return f"#{data['case_id']:04d}"

def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = []
        save()
    return data["users"][uid]

def countdown(deadline):
    now = datetime.now(VN_TZ)
    diff = deadline - now
    if diff.total_seconds() <= 0:
        return "🔴 **QUÁ HẠN**"
    return f"⏳ **{diff.days} ngày {diff.seconds // 3600} giờ**"

def make_embed(title, desc, color):
    e = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=datetime.now(VN_TZ)
    )
    e.set_footer(text=FOOTER, icon_url=ICON)
    return e

async def send_log(embed: discord.Embed):
    cid = data["config"].get("log_channel")
    if not cid:
        return
    ch = bot.get_channel(cid)
    if ch:
        await ch.send(embed=embed)

# ================= FAIL SAFE =================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    print("❌ Slash error:", error)
    if interaction.response.is_done():
        await interaction.followup.send("❌ Bot gặp lỗi nội bộ", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Bot gặp lỗi nội bộ", ephemeral=True)

# ================= CONFIRM VIEW =================
class ConfirmView(discord.ui.View):
    def __init__(self, member, record):
        super().__init__(timeout=120)
        self.member = member
        self.record = record

    @discord.ui.button(label="✅ ĐÃ ĐÓNG", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, _):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Admin only", ephemeral=True)

        self.record["paid"] = True
        self.record["paid_at"] = datetime.now(VN_TZ).isoformat()
        save()

        e = make_embed(
            "✅ XÁC NHẬN ĐÓNG PHẠT",
            f"{self.member.mention} đã hoàn tất hình phạt.",
            0x2ecc71
        )
        await interaction.response.edit_message(embed=e, view=None)
        await send_log(e)

# ================= MODAL =================
class GhiSeoModal(discord.ui.Modal, title="⚔️ GHI SẸO CIARA"):
    lydo = discord.ui.TextInput(
        label="📌 Lý do vi phạm",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        u = get_user(self.member.id)
        count = len(u) + 1

        record = {
            "case": next_case(),
            "reason": self.lydo.value,
            "by": interaction.user.name,
            "deadline": (datetime.now(VN_TZ) + timedelta(days=DEADLINE_DAYS)).isoformat(),
            "paid": False
        }

        u.append(record)
        save()

        e = make_embed(
            "⚔️ CIARA DISCIPLINE REPORT",
            (
                f"👤 {self.member.mention}\n"
                f"🧾 `{record['case']}`\n"
                f"📌 ```{record['reason']}```\n"
                f"🚨 **{PENALTY.get(count,'—')}**\n"
                f"{countdown(datetime.fromisoformat(record['deadline']))}"
            ),
            COLOR.get(min(count, 3), 0x992d22)
        )

        await interaction.followup.send(
            content=f"@everyone ⚠️ {self.member.mention}",
            embed=e,
            view=ConfirmView(self.member, record)
        )
        await send_log(e)

# ================= COMMANDS =================
@bot.tree.command(name="ghiseo")
async def ghiseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="xemseo")
async def xemseo(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.response.send_message("✨ Bạn sạch sẹo", ephemeral=True)

    r = u[-1]
    await interaction.response.send_message(
        embed=make_embed(
            "🧬 HỒ SƠ SẸO",
            f"🧾 `{r['case']}`\n📌 ```{r['reason']}```",
            COLOR.get(min(len(u), 3), 0x95a5a6)
        ),
        ephemeral=True
    )

@bot.tree.command(name="datkenhlog")
async def datkenhlog(interaction: discord.Interaction, kenh: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user):
        return await interaction.followup.send("❌ Admin only")

    data["config"]["log_channel"] = kenh.id
    save()
    await interaction.followup.send(f"✅ Đã đặt kênh log: {kenh.mention}")

@bot.tree.command(name="resync")
async def resync(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()

    await interaction.followup.send("✅ Đã resync")

# ================= READY =================
@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        else:
            await bot.tree.sync()
        print("⚔️ CIARA BOT ONLINE")
    except Exception:
        traceback.print_exc()

bot.run(TOKEN)
