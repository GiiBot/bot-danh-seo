import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import json, os

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DATA_FILE = "data.json"
VN_TZ = timezone(timedelta(hours=7))

# ================= CIARA THEME =================
CIARA_LEVEL_COLOR = {1: 0x8B0000, 2: 0xB30000, 3: 0x0F0F0F}
CIARA_FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
CIARA_ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"
CIARA_BANNER_BY_LEVEL = {
    1: "https://i.imgur.com/RED_LV1.png",
    2: "https://i.imgur.com/RED_LV2.png",
    3: "https://i.imgur.com/BLACK_LV3.png"
}

# ================= RP PENALTY =================
PENALTY_RULES = {
    2: "🔨 Đóng quỹ 400IG",
    3: "⛓️ Đóng quỹ 1m IG",
    5: "👢 Kick khỏi crew",
    7: "🔨 Ban vĩnh viễn"
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

def save(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

data = load()

def next_case_id():
    data["case_id"] += 1
    save(data)
    return f"#{data['case_id']:04d}"

def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = []
        save(data)
    return data["users"][uid]

def is_admin(member: discord.Member):
    return member.guild_permissions.administrator

# ================= HELPERS =================
def get_ciara_banner(count):
    return CIARA_BANNER_BY_LEVEL.get(min(count, 3))

async def update_scar_roles(member, count):
    guild = member.guild
    for r in data["config"]["scar_roles"].values():
        role = discord.utils.get(guild.roles, name=r)
        if role and role in member.roles:
            await member.remove_roles(role)
    if count > 0:
        role = discord.utils.get(
            guild.roles,
            name=data["config"]["scar_roles"][str(min(count, 3))]
        )
        if role:
            await member.add_roles(role)

async def send_log(guild, embed):
    cid = data["config"].get("log_channel")
    if cid:
        ch = guild.get_channel(cid)
        if ch:
            await ch.send(embed=embed)

async def send_dm(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass

# ================= PAGINATOR =================
class SeoProfilePaginator(discord.ui.View):
    def __init__(self, user_id, page=0):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.page = page

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id or is_admin(interaction.user)

    def build(self, guild):
        records = data["users"].get(str(self.user_id), [])[::-1]
        self.page = max(0, min(self.page, len(records) - 1))
        r = records[self.page]

        member = guild.get_member(self.user_id)
        name = member.display_name if member else self.user_id
        avatar = member.display_avatar.url if member else None
        total = len(records)

        embed = discord.Embed(
            title=f"🧬 HỒ SƠ SẸO | {name}",
            description=f"☠️ **Tổng sẹo:** `{total}`\n🧾 **Case:** `{r['case']}`",
            color=CIARA_LEVEL_COLOR.get(min(total, 3))
        )

        embed.add_field(name="📌 LÝ DO VI PHẠM", value=f"> {r['reason']}", inline=False)
        embed.add_field(name="👤 GHI BỞI", value=r["by"], inline=True)
        embed.add_field(name="🕒 THỜI GIAN", value=r["time"], inline=True)

        if avatar:
            embed.set_thumbnail(url=avatar)

        banner = get_ciara_banner(total)
        if banner:
            embed.set_image(url=banner)

        embed.set_footer(
            text=f"{CIARA_FOOTER} • Trang {self.page + 1}/{total}",
            icon_url=CIARA_ICON
        )
        return embed

    @discord.ui.button(label="⬅️ Trước", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, _):
        self.page -= 1
        await interaction.response.edit_message(embed=self.build(interaction.guild), view=self)

    @discord.ui.button(label="➡️ Sau", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, _):
        self.page += 1
        await interaction.response.edit_message(embed=self.build(interaction.guild), view=self)

# ================= TOPSEO VIEW =================
class TopSeoSelectView(discord.ui.View):
    def __init__(self, ranking):
        super().__init__(timeout=60)
        self.select = discord.ui.Select(
            placeholder="☠️ Chọn người để xem hồ sơ sẹo",
            options=[
                discord.SelectOption(
                    label=f"{count} sẹo",
                    description=f"Xem hồ sơ ID {uid}",
                    emoji="☠️",
                    value=str(uid)
                ) for uid, count in ranking
            ]
        )
        self.select.callback = self.callback
        self.add_item(self.select)

    async def callback(self, interaction):
        uid = int(self.select.values[0])
        paginator = SeoProfilePaginator(uid)
        await interaction.response.send_message(
            embed=paginator.build(interaction.guild),
            view=paginator,
            ephemeral=True
        )

# ================= MODAL =================
class GhiSeoModal(discord.ui.Modal, title="⚔️ GHI SẸO – LORD OF CIARA"):
    ly_do = discord.ui.TextInput(
        label="📌 Lý do vi phạm",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        u = get_user(self.member.id)
        case_id = next_case_id()
        week = datetime.now(VN_TZ).isocalendar()[1]

        u.append({
            "case": case_id,
            "reason": self.ly_do.value,
            "by": interaction.user.name,
            "time": datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M"),
            "week": week
        })
        save(data)

        scar_count = len(u)
        await update_scar_roles(self.member, scar_count)

        embed = discord.Embed(
            title="⚔️ CIARA DISCIPLINE REPORT",
            description=(
                f"👤 **Thành viên:** {self.member.mention}\n"
                f"🧾 **Case:** `{case_id}`\n"
                f"☠️ **Tổng sẹo:** `{scar_count}`"
            ),
            color=CIARA_LEVEL_COLOR.get(min(scar_count, 3))
        )
        embed.add_field(name="📌 LÝ DO", value=f"> {self.ly_do.value}", inline=False)

        penalty = PENALTY_RULES.get(scar_count)
        if penalty:
            embed.add_field(name="⚠️ HÌNH PHẠT RP", value=penalty, inline=False)

        embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

        data["admin_logs"].append({
            "action": "ghiseo",
            "admin": interaction.user.name,
            "target": self.member.id,
            "time": datetime.now(VN_TZ).strftime("%d/%m %H:%M")
        })
        save(data)

        await interaction.followup.send(content=f"@everyone ⚠️ {self.member.mention}", embed=embed)
        await send_log(interaction.guild, embed)
        await send_dm(self.member, embed)

# ================= SLASH COMMANDS =================
@bot.tree.command(name="ghiseo", description="⚔️ Ghi sẹo cho thành viên")
async def ghiseo(interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Không có quyền", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="xemseo", description="👁️ Xem hồ sơ sẹo của bạn")
async def xemseo(interaction):
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.response.send_message("✨ Bạn là công dân sạch.", ephemeral=True)
    paginator = SeoProfilePaginator(interaction.user.id)
    await interaction.response.send_message(
        embed=paginator.build(interaction.guild),
        view=paginator,
        ephemeral=True
    )

@bot.tree.command(name="topseo", description="☠️ Bảng tử hình – BXH sẹo")
async def topseo(interaction):
    ranking = [(int(uid), len(v)) for uid, v in data["users"].items() if v]
    if not ranking:
        return await interaction.response.send_message("✨ Chưa có ai bị ghi sẹo.", ephemeral=True)

    ranking.sort(key=lambda x: x[1], reverse=True)
    ranking = ranking[:10]

    embed = discord.Embed(
        title="☠️ BẢNG TỬ HÌNH – LORD OF CIARA",
        description="👑 Top cá nhân vi phạm nhiều nhất",
        color=0x0F0F0F
    )

    for i, (uid, count) in enumerate(ranking, 1):
        member = interaction.guild.get_member(uid)
        icon = "👑" if i == 1 else "☠️"
        embed.add_field(
            name=f"{icon} #{i} | {member.display_name if member else uid}",
            value=f"**Sẹo:** `{count}`",
            inline=False
        )

    embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)
    await interaction.response.send_message(embed=embed, view=TopSeoSelectView(ranking))

@bot.tree.command(name="thongke", description="📊 Thống kê sẹo theo tuần")
async def thongke(interaction):
    week = datetime.now(VN_TZ).isocalendar()[1]
    stats = {}

    for uid, records in data["users"].items():
        for r in records:
            if r.get("week") == week:
                stats[uid] = stats.get(uid, 0) + 1

    if not stats:
        return await interaction.response.send_message("✨ Tuần này không có vi phạm.", ephemeral=True)

    embed = discord.Embed(
        title=f"📊 THỐNG KÊ TUẦN {week}",
        description="☠️ Danh sách vi phạm trong tuần",
        color=0xB30000
    )

    for uid, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        member = interaction.guild.get_member(int(uid))
        embed.add_field(
            name=f"☠️ {member.display_name if member else uid}",
            value=f"`{count}` sẹo",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="lichsuadmin", description="🧾 Lịch sử admin thao tác")
async def lichsuadmin(interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Admin only", ephemeral=True)

    logs = data["admin_logs"][-10:]
    embed = discord.Embed(title="🧾 LỊCH SỬ ADMIN", color=0x0F0F0F)

    for l in logs:
        embed.add_field(
            name=l["action"],
            value=f"{l['admin']} → {l['target']} ({l['time']})",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= READY =================
@bot.tree.command(name="datkenhlog", description="📥 Đặt kênh log sẹo")
async def datkenhlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ Chỉ Admin mới dùng được lệnh này",
            ephemeral=True
        )

    data["config"]["log_channel"] = channel.id
    save(data)

    await interaction.response.send_message(
        f"✅ Đã đặt kênh log sẹo: {channel.mention}",
        ephemeral=True
    )

@bot.event
async def on_ready():
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()
    print(f"⚔️ CIARA BOT ONLINE: {bot.user}")

bot.run(TOKEN)
