import discord
from discord.ext import commands
from datetime import datetime
import json, os, traceback

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DATA_FILE = "data.json"

# ================= CIARA THEME =================
CIARA_LEVEL_COLOR = {
    1: 0x8B0000,
    2: 0xB30000,
    3: 0x0F0F0F
}

CIARA_FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
CIARA_ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"

CIARA_BANNER_BY_LEVEL = {
    1: "https://i.imgur.com/RED_LV1.png",
    2: "https://i.imgur.com/RED_LV2.png",
    3: "https://i.imgur.com/BLACK_LV3.png"
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
                "scar_roles": {
                    "1": "Sẹo 1",
                    "2": "Sẹo 2",
                    "3": "Sẹo 3"
                }
            },
            "case_id": 0,
            "users": {}
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "case_id" not in data:
        data["case_id"] = 0
    return data

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
    return data["users"][uid]

# ================= PERMISSION =================
def is_admin(member: discord.Member):
    return member.guild_permissions.administrator

# ================= CIARA HELPERS =================
def get_ciara_banner(scar_count: int):
    if scar_count >= 3:
        return CIARA_BANNER_BY_LEVEL[3]
    return CIARA_BANNER_BY_LEVEL.get(scar_count)

async def update_scar_roles(member, count):
    try:
        guild = member.guild
        scar_roles = data["config"]["scar_roles"]

        for rname in scar_roles.values():
            role = discord.utils.get(guild.roles, name=rname)
            if role and role in member.roles:
                await member.remove_roles(role)

        if count > 0:
            level = str(min(count, 3))
            role = discord.utils.get(guild.roles, name=scar_roles[level])
            if role:
                await member.add_roles(role)
    except Exception as e:
        print("ROLE ERROR:", e)

async def send_log(guild, embed):
    cid = data["config"].get("log_channel")
    if not cid:
        return
    ch = guild.get_channel(cid)
    if ch:
        await ch.send(embed=embed)

async def send_dm(member, embed):
    try:
        await member.send(embed=embed)
    except Exception:
        pass

# ================= VIEW / PAGINATOR =================
class SeoProfilePaginator(discord.ui.View):
    def __init__(self, user_id: int, page: int = 0):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.page = page

    def build(self, guild):
        records = data["users"].get(str(self.user_id), [])
        total = len(records)
        records = records[::-1]

        member = guild.get_member(self.user_id)
        name = member.display_name if member else f"ID {self.user_id}"
        avatar = member.display_avatar.url if member else None
        r = records[self.page]

        embed = discord.Embed(
            title=f"🧬 HỒ SƠ SẸO – {name}",
            description=f"🧾 **Case `{r['case']}`**",
            color=CIARA_LEVEL_COLOR.get(min(total, 3), 0x8B0000)
        )
        embed.add_field(name="📌 Lý do", value=f"```{r['reason']}```", inline=False)
        embed.add_field(name="👤 Ghi bởi", value=r["by"])
        embed.add_field(name="🕒 Thời gian", value=r["time"])
        embed.add_field(name="☠️ Tổng sẹo", value=str(total), inline=False)

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

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.build(interaction.guild), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        records = data["users"].get(str(self.user_id), [])
        if self.page < len(records) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.build(interaction.guild), view=self)
        else:
            await interaction.response.defer()

class SeoProfileEntryView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="📄 Xem hồ sơ sẹo", style=discord.ButtonStyle.danger)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        records = data["users"].get(str(self.user_id), [])
        if not records:
            return await interaction.response.send_message(
                "✨ Thành viên này không có sẹo.",
                ephemeral=True
            )
        paginator = SeoProfilePaginator(self.user_id)
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
        max_length=300,
        required=True
    )

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        await ghiseo_core(interaction, self.member, self.ly_do.value)

# ================= CORE =================
async def ghiseo_core(interaction, member, ly_do):
    await interaction.response.defer()

    if not is_admin(interaction.user):
        return await interaction.followup.send("❌ Bạn không có quyền", ephemeral=True)

    u = get_user(member.id)
    case_id = next_case_id()

    u.append({
        "case": case_id,
        "reason": ly_do,
        "by": interaction.user.name,
        "time": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    save(data)

    scar_count = len(u)
    await update_scar_roles(member, scar_count)

    embed = discord.Embed(
        title="⚔️ GHI NHẬN SẸO – LORD OF CIARA",
        description="🩸 **Vết sẹo đã được ghi vào hồ sơ**",
        color=CIARA_LEVEL_COLOR.get(min(scar_count, 3))
    )
    embed.add_field(name="🧾 Case ID", value=case_id)
    embed.add_field(name="👤 Thành viên", value=member.mention, inline=False)
    embed.add_field(name="📌 Lý do", value=f"```{ly_do}```", inline=False)
    embed.add_field(name="☠️ Tổng sẹo", value=str(scar_count))
    embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

    await interaction.followup.send(content=f"@everyone ⚠️ {member.mention}", embed=embed)
    await send_log(interaction.guild, embed)
    await send_dm(member, embed)

# ================= SLASH COMMANDS =================
@bot.tree.command(name="ghiseo", description="⚔️ Ghi sẹo cho thành viên")
async def ghiseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Bạn không có quyền", ephemeral=True)
    await interaction.response.send_modal(GhiSeoModal(member))

@bot.tree.command(name="goiseo", description="➖ Gỡ 1 sẹo")
async def goiseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Bạn không có quyền", ephemeral=True)
    u = get_user(member.id)
    if not u:
        return await interaction.response.send_message("⚠️ Không có sẹo", ephemeral=True)
    u.pop()
    save(data)
    await update_scar_roles(member, len(u))
    await interaction.response.send_message(f"✅ Đã gỡ 1 sẹo cho {member.mention}")

@bot.tree.command(name="resetseo", description="♻️ Xoá sạch sẹo")
async def resetseo(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Bạn không có quyền", ephemeral=True)
    data["users"][str(member.id)] = []
    save(data)
    await update_scar_roles(member, 0)
    await interaction.response.send_message(f"♻️ Đã reset sẹo cho {member.mention}")

@bot.tree.command(name="xemseo", description="👁️ Xem sẹo của bạn")
async def xemseo(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    if not u:
        return await interaction.response.send_message(
            "✨ Bạn là công dân sạch của CIARA",
            ephemeral=True
        )
    paginator = SeoProfilePaginator(interaction.user.id)
    await interaction.response.send_message(
        embed=paginator.build(interaction.guild),
        view=paginator,
        ephemeral=True
    )

@bot.tree.command(name="datkenhlog", description="📥 Đặt kênh log sẹo")
async def datkenhlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Chỉ Admin", ephemeral=True)
    data["config"]["log_channel"] = channel.id
    save(data)
    await interaction.response.send_message(f"✅ Đã đặt kênh log: {channel.mention}")

@bot.tree.command(name="topseo", description="☠️ Bảng tử hình – BXH sẹo")
async def topseo(interaction: discord.Interaction):
    ranking = [
        (int(uid), len(v))
        for uid, v in data["users"].items() if v
    ]
    if not ranking:
        return await interaction.response.send_message(
            "✨ Chưa có ai bị ghi sẹo.",
            ephemeral=True
        )

    ranking.sort(key=lambda x: x[1], reverse=True)
    ranking = ranking[:10]

    embed = discord.Embed(
        title="☠️ BẢNG TỬ HÌNH – LORD OF CIARA",
        color=0x0F0F0F
    )

    for i, (uid, count) in enumerate(ranking, 1):
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else f"ID {uid}"
        embed.add_field(
            name=f"#{i} ☠️ {name}",
            value=f"`{count}` sẹo",
            inline=False
        )

    embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)
    view = SeoProfileEntryView(ranking[0][0])
    await interaction.response.send_message(embed=embed, view=view)

# ================= READY =================
@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"Slash commands synced to guild {GUILD_ID}")
        else:
            await bot.tree.sync()
            print("Slash commands synced globally")
    except Exception as e:
        print("SYNC ERROR:", e)
    print(f"CIARA BOT ONLINE: {bot.user}")

# ================= START =================
if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_TOKEN missing")
    else:
        bot.run(TOKEN)
