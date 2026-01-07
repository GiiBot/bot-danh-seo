import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import json, os

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DATA_FILE = "data.json"
VN_TZ = timezone(timedelta(hours=7))

# ================= THEME =================
CIARA_LEVEL_COLOR = {1: 0x8B0000, 2: 0xB30000, 3: 0x0F0F0F}
CIARA_FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
CIARA_ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"

# ================= PENALTY =================
PENALTY_RULES = {
    2: "Đóng quỹ 400IG",
    3: "Đóng quỹ 1.000.000 IG",
    5: "Kick khỏi crew",
    7: "Ban vĩnh viễn"
}

# ================= BOT =================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SAFE DEFER =================
async def safe_defer(interaction, ephemeral=False):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=ephemeral)

# ================= DATA =================
def load():
    if not os.path.exists(DATA_FILE):
        return {
            "config": {
                "log_channel": None,
                "scar_roles": {"1": "Sẹo 1", "2": "Sẹo 2", "3": "Sẹo 3"}
            },
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
data.setdefault("admin_logs", [])

def is_admin(m): 
    return m.guild_permissions.administrator

def next_case_id():
    data["case_id"] += 1
    save()
    return f"#{data['case_id']:04d}"

def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = []
        save()
    return data["users"][uid]

# ================= ROLE =================
async def update_scar_roles(member, count):
    for r in data["config"]["scar_roles"].values():
        role = discord.utils.get(member.guild.roles, name=r)
        if role and role in member.roles:
            await member.remove_roles(role)
    if count > 0:
        role = discord.utils.get(
            member.guild.roles,
            name=data["config"]["scar_roles"][str(min(count, 3))]
        )
        if role:
            await member.add_roles(role)

# ================= EMBED BUILD =================
def build_penalty_embed(member, record, total):
    embed = discord.Embed(
        title="⚔️ CIARA DISCIPLINE REPORT",
        description=(
            f"👤 **Thành viên:** {member.mention}\n"
            f"🧾 **Case:** `{record['case']}`\n"
            f"☠️ **Tổng sẹo:** `{total}`"
        ),
        color=CIARA_LEVEL_COLOR.get(min(total, 3))
    )

    embed.add_field(
        name="📌 LÝ DO VI PHẠM",
        value=f"```{record['reason']}```",
        inline=False
    )

    penalty = PENALTY_RULES.get(total)
    if penalty:
        status = "✅ **ĐÃ ĐÓNG PHẠT**" if record["paid"] else "❌ **CHƯA ĐÓNG PHẠT**"
        embed.add_field(
            name="🚨 HÌNH PHẠT RP (BẮT BUỘC)",
            value=f"⚠️ **{penalty.upper()}**\n\n🧾 Trạng thái: {status}",
            inline=False
        )

    embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)
    return embed

# ================= MODAL =================
class GhiSeoModal(discord.ui.Modal, title="⚔️ GHI SẸO – CIARA"):
    ly_do = discord.ui.TextInput(label="Lý do vi phạm", style=discord.TextStyle.paragraph)

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction):
        await safe_defer(interaction, True)

        u = get_user(self.member.id)
        cid = next_case_id()
        record = {
            "case": cid,
            "reason": self.ly_do.value,
            "by": interaction.user.name,
            "time": datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M"),
            "week": datetime.now(VN_TZ).isocalendar()[1],
            "paid": False
        }
        u.append(record)
        save()

        await update_scar_roles(self.member, len(u))

        embed = build_penalty_embed(self.member, record, len(u))

        data["admin_logs"].append({
            "action": "ghiseo",
            "admin": interaction.user.name,
            "target": self.member.id,
            "time": datetime.now(VN_TZ).strftime("%d/%m %H:%M")
        })
        save()

        await interaction.followup.send(f"@everyone ⚠️ {self.member.mention}", embed=embed)

# ================= SLASH COMMANDS =================
@bot.tree.command(name="ghiseo")
async def ghiseo(interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="xacnhanphat")
async def xacnhanphat(interaction, member: discord.Member):
    await safe_defer(interaction, True)
    if not is_admin(interaction.user):
        return await interaction.followup.send("❌ Admin only", ephemeral=True)

    u = get_user(member.id)
    if not u:
        return await interaction.followup.send("⚠️ Không có sẹo", ephemeral=True)

    u[-1]["paid"] = True
    save()

    embed = build_penalty_embed(member, u[-1], len(u))
    await interaction.followup.send(f"✅ Đã xác nhận **ĐÃ ĐÓNG PHẠT** cho {member.mention}", embed=embed)

@bot.tree.command(name="xemseo")
async def xemseo(interaction):
    await safe_defer(interaction, True)
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.followup.send("✨ Bạn là công dân sạch", ephemeral=True)

    r = u[-1]
    embed = build_penalty_embed(interaction.user, r, len(u))
    await interaction.followup.send(embed=embed, ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
    print(f"⚔️ CIARA BOT ONLINE: {bot.user}")

bot.run(TOKEN)
