import discord
from discord.ext import commands
from datetime import datetime
import json, os, asyncio, traceback

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "data.json"

# ================= CIARA THEME =================
CIARA_LEVEL_COLOR = {
    1: 0x8B0000,
    2: 0xB30000,
    3: 0x0F0F0F
}
CIARA_FOOTER = "⚔️ LORD OF CIARA | KỶ LUẬT TẠO SỨC MẠNH"
CIARA_ICON = "https://cdn-icons-png.flaticon.com/512/1695/1695213.png"

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
    return data["users"][uid]

# ================= PERMISSION =================
def is_admin(member: discord.Member):
    return member.guild_permissions.administrator

# ================= SAFE ROLE HANDLER =================
async def update_scar_roles(member, count):
    try:
        guild = member.guild
        scar_roles = data["config"]["scar_roles"]

        # remove old
        for rname in scar_roles.values():
            role = discord.utils.get(guild.roles, name=rname)
            if role and role in member.roles:
                await member.remove_roles(role)

        # add new
        if count > 0:
            level = str(min(count, 3))
            role = discord.utils.get(guild.roles, name=scar_roles[level])
            if role:
                await member.add_roles(role)

    except Exception as e:
        print("❌ ROLE ERROR:", e)

# ================= SAFE SEND =================
async def safe_followup(interaction, **kwargs):
    try:
        await interaction.followup.send(**kwargs)
    except Exception as e:
        print("❌ FOLLOWUP ERROR:", e)

async def send_log(guild, embed):
    try:
        cid = data["config"]["log_channel"]
        if cid:
            ch = guild.get_channel(cid)
            if ch:
                await ch.send(embed=embed)
    except Exception as e:
        print("❌ LOG ERROR:", e)

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🟢 CIARA SCAR BOT ONLINE: {bot.user}")

@bot.event
async def on_error(event, *args):
    traceback.print_exc()

# ================= COMMANDS =================

@bot.tree.command(name="ghiseo", description="⚔️ Ghi sẹo cho thành viên")
async def ghiseo(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    await interaction.response.defer(ephemeral=False)

    try:
        if not is_admin(interaction.user):
            return await safe_followup(interaction, content="❌ Bạn không có quyền", ephemeral=True)

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
            color=CIARA_LEVEL_COLOR.get(min(scar_count, 3), 0x8B0000)
        )
        embed.add_field(name="🧾 Case ID", value=f"`{case_id}`")
        embed.add_field(name="👤 Thành viên", value=member.mention, inline=False)
        embed.add_field(name="📌 Lý do", value=f"```{ly_do}```", inline=False)
        embed.add_field(name="☠️ Tổng sẹo", value=f"**{scar_count}**")
        embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

        await safe_followup(interaction, embed=embed)
        await send_log(interaction.guild, embed)

    except Exception as e:
        print("❌ GHISEO ERROR:", e)
        await safe_followup(interaction, content="⚠️ Đã ghi sẹo nhưng có lỗi phụ (Admin check log)")

@bot.tree.command(name="goiseo", description="➖ Gỡ 1 sẹo")
async def goiseo(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()

    try:
        if not is_admin(interaction.user):
            return await safe_followup(interaction, content="❌ Bạn không có quyền", ephemeral=True)

        u = get_user(member.id)
        if not u:
            return await safe_followup(interaction, content="⚠️ Thành viên không có sẹo")

        u.pop()
        save(data)
        await update_scar_roles(member, len(u))

        embed = discord.Embed(
            title="🔥 GIẢM SẸO",
            description=f"{member.mention} đã được xoá 1 sẹo",
            color=0x1ABC9C
        )
        embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

        await safe_followup(interaction, embed=embed)
        await send_log(interaction.guild, embed)

    except Exception as e:
        print("❌ GOISEO ERROR:", e)
        await safe_followup(interaction, content="⚠️ Có lỗi nhưng bot không bị treo")

@bot.tree.command(name="resetseo", description="♻️ Xoá sạch sẹo")
async def resetseo(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()

    try:
        if not is_admin(interaction.user):
            return await safe_followup(interaction, content="❌ Bạn không có quyền", ephemeral=True)

        data["users"][str(member.id)] = []
        save(data)
        await update_scar_roles(member, 0)

        embed = discord.Embed(
            title="🏴‍☠️ ÂN XÁ CIARA",
            description=f"Hồ sơ {member.mention} đã được làm sạch",
            color=0xC9A227
        )
        embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

        await safe_followup(interaction, embed=embed)
        await send_log(interaction.guild, embed)

    except Exception as e:
        print("❌ RESETSEO ERROR:", e)
        await safe_followup(interaction, content="⚠️ Có lỗi nhưng bot vẫn sống")

@bot.tree.command(name="xemseo", description="👁️ Xem sẹo của bạn")
async def xemseo(interaction: discord.Interaction):
    try:
        u = get_user(interaction.user.id)
        if not u:
            return await interaction.response.send_message(
                "✨ Bạn là công dân sạch của **LORD OF CIARA**",
                ephemeral=True
            )

        desc = "\n".join(
            f"🧾 `{v['case']}` | ⚠️ {v['reason']} _(by {v['by']})_"
            for v in u
        )

        embed = discord.Embed(
            title="👁️ HỒ SƠ SẸO CÁ NHÂN",
            description=desc,
            color=0x2980B9
        )
        embed.add_field(name="☠️ Tổng sẹo", value=f"**{len(u)}**")
        embed.set_footer(text=CIARA_FOOTER, icon_url=CIARA_ICON)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print("❌ XEMSEO ERROR:", e)

# ================= START =================
if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN chưa được thiết lập")
    else:
        bot.run(TOKEN)
