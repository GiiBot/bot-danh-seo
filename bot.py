import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import json, os

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

# ================= PENALTY =================
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
def load():
    if not os.path.exists(DATA_FILE):
        return {
            "config": {"log_channel": None},
            "case_id": 0,
            "users": {},
            "admin_logs": []
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load()

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

def is_admin(m: discord.Member):
    return m.guild_permissions.administrator

def countdown(deadline):
    now = datetime.now(VN_TZ)
    diff = deadline - now
    if diff.total_seconds() <= 0:
        return "🔴 **QUÁ HẠN**"
    return f"⏳ **{diff.days} ngày {diff.seconds//3600} giờ**"

def embed(title, desc, color):
    e = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(VN_TZ))
    e.set_footer(text=FOOTER, icon_url=ICON)
    return e

# ================= AUTO PING =================
@tasks.loop(hours=6)
async def auto_ping():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    for uid, records in data["users"].items():
        member = guild.get_member(int(uid))
        if not member:
            continue
        for r in records:
            if not r["paid"]:
                deadline = datetime.fromisoformat(r["deadline"])
                if (deadline - datetime.now(VN_TZ)).days <= 1:
                    try:
                        await member.send(
                            f"🔔 **NHẮC ĐÓNG PHẠT**\n"
                            f"🧾 Case `{r['case']}`\n"
                            f"{countdown(deadline)}"
                        )
                    except:
                        pass

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
        await interaction.response.edit_message(
            embed=embed(
                "✅ XÁC NHẬN ĐÓNG PHẠT",
                f"{self.member.mention} đã hoàn tất hình phạt.",
                0x27ae60
            ),
            view=None
        )

    @discord.ui.button(label="❌ HỦY", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(content="❌ Đã hủy", view=None)

# ================= MODAL GHI SẸO =================
class GhiSeoModal(discord.ui.Modal, title="⚔️ GHI SẸO CIARA"):
    lydo = discord.ui.TextInput(label="📌 Lý do vi phạm", style=discord.TextStyle.paragraph)

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

        e = embed(
            "⚔️ CIARA DISCIPLINE REPORT",
            (
                f"👤 {self.member.mention}\n"
                f"🧾 `{record['case']}`\n"
                f"📌 ```{record['reason']}```\n"
                f"🚨 **{PENALTY.get(count,'—')}**\n"
                f"{countdown(datetime.fromisoformat(record['deadline']))}"
            ),
            COLOR.get(min(count,3))
        )
        await interaction.followup.send(f"@everyone ⚠️ {self.member.mention}", embed=e)

# ================= COMMANDS =================
@bot.tree.command(name="ghiseo")
async def ghiseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="goiseo")
async def goiseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    u = get_user(member.id)
    if not u:
        return await interaction.response.send_message("⚠️ Không có sẹo", ephemeral=True)
    u.pop()
    save()
    await interaction.response.send_message(f"✅ Đã gỡ 1 sẹo cho {member.mention}")

@bot.tree.command(name="resetseo")
async def resetseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    data["users"][str(member.id)] = []
    save()
    await interaction.response.send_message(f"♻️ Đã reset sẹo cho {member.mention}")

@bot.tree.command(name="xemseo")
async def xemseo(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.response.send_message("✨ Bạn sạch sẹo", ephemeral=True)
    r = u[-1]
    await interaction.response.send_message(
        embed=embed(
            "🧬 HỒ SƠ SẸO",
            f"🧾 `{r['case']}`\n📌 ```{r['reason']}```",
            COLOR.get(min(len(u),3))
        ),
        ephemeral=True
    )

@bot.tree.command(name="dashboard")
async def dashboard(interaction: discord.Interaction):
    total = sum(len(v) for v in data["users"].values())
    unpaid = sum(1 for v in data["users"].values() for r in v if not r["paid"])
    await interaction.response.send_message(
        embed=embed(
            "📊 DASHBOARD CIARA",
            f"📁 Tổng case: **{total}**\n❌ Chưa đóng: **{unpaid}**",
            0x3498db
        )
    )

@bot.tree.command(name="resync")
async def resync(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)
    await interaction.response.send_message("✅ Đã resync", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    if not auto_ping.is_running():
        auto_ping.start()
    print("⚔️ CIARA BOT ONLINE")

bot.run(TOKEN)
