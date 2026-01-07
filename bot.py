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
CIARA_COLOR = {1: 0x8B0000, 2: 0xB30000, 3: 0x0F0F0F}
FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"

# ================= PENALTY =================
PENALTY_RULES = {
    1: "Cảnh cáo",
    2: "Đóng quỹ 400 IG",
    3: "Đóng quỹ 1.000.000 IG",
    5: "Kick khỏi crew",
    7: "Ban vĩnh viễn"
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
data.setdefault("admin_logs", [])

# ================= UTILS =================
def is_admin(m): 
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

async def send_log(guild, embed):
    cid = data["config"].get("log_channel")
    if cid:
        ch = guild.get_channel(cid)
        if ch:
            await ch.send(embed=embed)

# ================= EMBED =================
def build_embed(member, record, total):
    embed = discord.Embed(
        title="⚔️ CIARA DISCIPLINE REPORT",
        description=(
            f"👤 **Thành viên:** {member.mention}\n"
            f"🧾 **Case:** `{record['case']}`\n"
            f"☠️ **Tổng sẹo:** `{total}`"
        ),
        color=CIARA_COLOR.get(min(total, 3))
    )

    embed.add_field(
        name="📌 LÝ DO",
        value=f"```{record['reason']}```",
        inline=False
    )

    penalty = PENALTY_RULES.get(total, "—")
    status = "✅ **ĐÃ ĐÓNG**" if record["paid"] else "❌ **CHƯA ĐÓNG**"
    note = record.get("paid_note", "—")

    embed.add_field(
        name="🚨 HÌNH PHẠT RP",
        value=f"⚠️ **{penalty}**\n🧾 Trạng thái: {status}\n💰 Ghi chú: **{note}**",
        inline=False
    )

    embed.set_footer(text=FOOTER, icon_url=ICON)
    return embed

# ================= VIEW CONFIRM =================
class ConfirmPaidView(discord.ui.View):
    def __init__(self, member, record):
        super().__init__(timeout=60)
        self.member = member
        self.record = record

    @discord.ui.button(label="✅ XÁC NHẬN ĐÃ ĐÓNG", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, _):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Admin only", ephemeral=True)

        self.record["paid"] = True
        self.record["paid_note"] = "Đã xác nhận"
        save()

        embed = build_embed(self.member, self.record, len(get_user(self.member.id)))
        await interaction.response.edit_message(
            content="✅ **ĐÃ XÁC NHẬN ĐÓNG PHẠT**",
            embed=embed,
            view=None
        )

    @discord.ui.button(label="❌ HỦY", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction, _):
        await interaction.response.edit_message(
            content="❌ Đã hủy xác nhận",
            view=None
        )

# ================= MODAL =================
class GhiSeoModal(discord.ui.Modal, title="⚔️ GHI SẸO – CIARA"):
    ly_do = discord.ui.TextInput(label="Lý do vi phạm", style=discord.TextStyle.paragraph)

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction):
        record = {
            "case": next_case(),
            "reason": self.ly_do.value,
            "by": interaction.user.name,
            "time": datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M"),
            "week": datetime.now(VN_TZ).isocalendar()[1],
            "paid": False,
            "paid_note": ""
        }

        get_user(self.member.id).append(record)
        save()

        embed = build_embed(self.member, record, len(get_user(self.member.id)))
        await interaction.response.send_message(
            f"@everyone ⚠️ {self.member.mention}",
            embed=embed
        )
        await send_log(interaction.guild, embed)

# ================= SLASH COMMANDS =================
@bot.tree.command(name="ghiseo")
async def ghiseo(interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="xemseo")
async def xemseo(interaction):
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.response.send_message("✨ Bạn là công dân sạch", ephemeral=True)
    embed = build_embed(interaction.user, u[-1], len(u))
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="xacnhanphat")
async def xacnhanphat(interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    u = get_user(member.id)
    if not u:
        return await interaction.response.send_message("⚠️ Không có sẹo", ephemeral=True)
    await interaction.response.send_message(
        embed=build_embed(member, u[-1], len(u)),
        view=ConfirmPaidView(member, u[-1])
    )

@bot.tree.command(name="chuadongphat")
async def chuadongphat(interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)

    embed = discord.Embed(title="📊 CHƯA ĐÓNG PHẠT", color=0xB30000)
    for uid, records in data["users"].items():
        for r in records:
            if not r["paid"]:
                member = interaction.guild.get_member(int(uid))
                embed.add_field(
                    name=member.display_name if member else uid,
                    value=f"Case `{r['case']}`",
                    inline=False
                )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="topseo")
async def topseo(interaction):
    ranking = [(uid, len(v)) for uid, v in data["users"].items() if v]
    ranking.sort(key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="☠️ TOP SEO CIARA", color=0x0F0F0F)

    for i, (uid, c) in enumerate(ranking[:10], 1):
        m = interaction.guild.get_member(int(uid))
        embed.add_field(
            name=f"#{i} {m.display_name if m else uid}",
            value=f"{c} sẹo",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="thongke")
async def thongke(interaction):
    week = datetime.now(VN_TZ).isocalendar()[1]
    embed = discord.Embed(title=f"📊 THỐNG KÊ TUẦN {week}", color=0xB30000)

    for uid, records in data["users"].items():
        count = sum(1 for r in records if r["week"] == week)
        if count:
            m = interaction.guild.get_member(int(uid))
            embed.add_field(
                name=m.display_name if m else uid,
                value=f"{count} sẹo",
                inline=False
            )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="datkenhlog")
async def datkenhlog(interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    data["config"]["log_channel"] = channel.id
    save()
    await interaction.response.send_message(f"✅ Đã đặt kênh log: {channel.mention}", ephemeral=True)

@bot.tree.command(name="resync")
async def resync(interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)
    await interaction.response.send_message("✅ Đã resync slash command", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)
    print("✅ Slash commands synced (GUILD)")
    print(f"⚔️ CIARA BOT ONLINE: {bot.user}")

bot.run(TOKEN)
