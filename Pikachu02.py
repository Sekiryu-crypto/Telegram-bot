from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatPermissions, ChatPrivileges
import asyncio
import time
import re
from datetime import datetime, timedelta
from googletrans import Translator

# --- CONFIG ---
API_ID = 22397733
API_HASH = "__"
BOT_TOKEN = "__"

# --- INIT ---
app = Client("group_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- DATA STORAGE ---
warnings = {}
notes = {}
filters_dict = {}
blacklist_words = ["spam", "badword"]
rules_text = "📜 Group Rules:\n1. Be respectful\n2. No spam\n3. Follow admin instructions"
welcome_message = "👋 Welcome {mention} to {title}!"
ADMINS_CACHE = {}

# --- HELPER FUNCTIONS ---

async def is_admin(client, chat_id: int, user_id: int) -> bool:
    """Check if a user is admin or owner in a chat, with caching."""
    if (chat_id, user_id) in ADMINS_CACHE:
        return ADMINS_CACHE[(chat_id, user_id)]
    try:
        member = await client.get_chat_member(chat_id, user_id)
        is_admin = member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
        ADMINS_CACHE[(chat_id, user_id)] = is_admin
        return is_admin
    except Exception:
        return False

async def resolve_user(client, message: Message):
    """Resolve user from reply, user ID, or username."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        user_ref = message.command[1]
        try:
            if user_ref.isdigit():
                return await client.get_users(int(user_ref))
            if user_ref.startswith("@"):
                return await client.get_users(user_ref[1:])
        except Exception as e:
            await message.reply(f"❌ User not found: {e}")
            return None
    return None

async def delete_message_with_delay(message: Message, delay=5):
    """Delete a message after a delay."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def purge_messages_in_chunks(client, chat_id, message_ids):
    """Delete messages in batches of up to 100."""
    for i in range(0, len(message_ids), 100):
        chunk = message_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id, chunk)
        except Exception:
            pass

def user_mention(user):
    """Return mention string for a user."""
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id})"

async def check_admin_and_reply(client, message: Message):
    """Check if user is admin and reply if not."""
    if not await is_admin(client, message.chat.id, message.from_user.id):
        await message.reply("⛔️ You need admin permissions!")
        return False
    return True

# --- BASIC COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    await message.reply("👋 Hello! I'm an advanced group management bot. Add me to a group and make me admin!")

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_text = """
🛠 **Advanced Group Management Bot**

👮 **Admin Tools:**
/ban [user] - Ban a user
/unban [user] - Unban a user
/kick [user] - Kick a user
/mute [user] [minutes] - Mute a user
/unmute [user] - Unmute a user
/warn [user] - Warn a user
/unwarn [user] - Remove warning
/warns [user] - Check warnings
/purge [reply] - Bulk delete messages
/pin [reply] - Pin a message
/unpin - Unpin current message
/settitle [text] - Change group title
/setphoto [reply] - Set group photo
/setdescription [text] - Set group description
/promote [user] - Promote to admin
/demote [user] - Demote admin

📝 **Group Features:**
/setrules [text] - Set group rules
/rules - Show rules
/setwelcome [text] - Set welcome message
/welcome - Show welcome
/report [reply] - Report to admins
/staff - Show admins

💾 **Utilities:**
/setnote [name] [text] - Save note
/getnote [name] - Get note
/id - Get user/chat ID
/info [user] - Get user info

🎉 **Fun:**
/slap [reply] - Slap a user
/roll - Roll a dice
/coin - Flip a coin
/say [text] - Make bot say something
    """
    await message.reply(help_text)

@app.on_message(filters.command("ping"))
async def ping(client, message: Message):
    start_time = time.time()
    reply = await message.reply("🏓 Pinging...")
    end_time = time.time()
    await reply.edit(f"🏓 Pong! `{round((end_time - start_time) * 1000, 2)}ms`")

# --- MODERATION COMMANDS ---

@app.on_message(filters.command("ban") & filters.group)
async def ban_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"🔨 Banned {user_mention(target)}", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"❌ Ban failed: {str(e)}")

@app.on_message(filters.command("unban") & filters.group)
async def unban_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ Unbanned {user_mention(target)}", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"❌ Unban failed: {str(e)}")

@app.on_message(filters.command("kick") & filters.group)
async def kick_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.ban_chat_member(
            message.chat.id,
            target.id,
            until_date=datetime.now() + timedelta(seconds=30)
        )
        await client.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"👢 Kicked {user_mention(target)}", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"❌ Kick failed: {str(e)}")

@app.on_message(filters.command("mute") & filters.group)
async def mute_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    duration = 60
    if len(message.command) > 2 and message.command[2].isdigit():
        duration = int(message.command[2])
    try:
        await client.restrict_chat_member(
            message.chat.id,
            target.id,
            ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=datetime.now() + timedelta(minutes=duration)
        )
        await message.reply(f"🔇 Muted {user_mention(target)} for {duration} minutes", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"❌ Mute failed: {str(e)}")

@app.on_message(filters.command("unmute") & filters.group)
async def unmute_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.restrict_chat_member(
            message.chat.id,
            target.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await message.reply(f"🔊 Unmuted {user_mention(target)}", disable_web_page_preview=True)
    except Exception as e:
        await message.reply(f"❌ Unmute failed: {str(e)}")

@app.on_message(filters.command("warn") & filters.group)
async def warn_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    user_id = target.id
    chat_id = message.chat.id
    warnings.setdefault(chat_id, {})
    warnings[chat_id].setdefault(user_id, 0)
    warnings[chat_id][user_id] += 1
    count = warnings[chat_id][user_id]
    if count >= 3:
        try:
            await client.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                ),
                until_date=datetime.now() + timedelta(hours=24)
            )
            warnings[chat_id][user_id] = 0
            await message.reply(f"🔇 Muted {user_mention(target)} for 24 hours due to 3 warnings.")
        except Exception as e:
            await message.reply(f"⚠️ Warning added but mute failed: {str(e)}")
    else:
        await message.reply(f"⚠️ Warned {user_mention(target)} (Warnings: {count}/3)")

@app.on_message(filters.command("unwarn") & filters.group)
async def unwarn_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    user_id = target.id
    chat_id = message.chat.id
    if warnings.get(chat_id, {}).get(user_id, 0) > 0:
        warnings[chat_id][user_id] -= 1
        count = warnings[chat_id][user_id]
        await message.reply(f"✅ Removed warning from {user_mention(target)} (Now: {count}/3)")
    else:
        await message.reply(f"ℹ️ {user_mention(target)} has no warnings.")

@app.on_message(filters.command("warns") & filters.group)
async def check_warns(client, message: Message):
    target = await resolve_user(client, message)
    if not target:
        target = message.from_user
    user_id = target.id
    chat_id = message.chat.id
    count = warnings.get(chat_id, {}).get(user_id, 0)
    await message.reply(f"⚠️ {user_mention(target)} has {count}/3 warnings.")

@app.on_message(filters.command("purge") & filters.group)
async def purge_messages(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if not message.reply_to_message:
        await message.reply("⚠️ Reply to the first message to purge from.")
        return
    try:
        start_id = message.reply_to_message.id
        end_id = message.id
        messages_to_delete = []
        async for msg in client.get_chat_history(
            chat_id=message.chat.id,
            offset_id=end_id + 1,
            limit=100,
            reverse=True,
        ):
            if msg.id < start_id:
                break
            if start_id <= msg.id <= end_id:
                messages_to_delete.append(msg.id)
        if not messages_to_delete:
            await message.reply("❌ No messages found to delete.")
            return
        await purge_messages_in_chunks(client, message.chat.id, messages_to_delete)
        notify = await message.reply(f"🧹 Deleted {len(messages_to_delete)} messages.")
        await delete_message_with_delay(notify, 5)
    except Exception as e:
        await message.reply(f"❌ Purge failed: {str(e)}")

@app.on_message(filters.command("pin") & filters.group)
async def pin_message(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if not message.reply_to_message:
        await message.reply("⚠️ Reply to a message to pin.")
        return
    try:
        await client.pin_chat_message(
            message.chat.id,
            message.reply_to_message.id,
            disable_notification=True
        )
        await message.reply("📌 Message pinned.")
    except Exception as e:
        await message.reply(f"❌ Pin failed: {str(e)}")

@app.on_message(filters.command("unpin") & filters.group)
async def unpin_message(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    try:
        await client.unpin_chat_message(message.chat.id)
        await message.reply("📌 Message unpinned.")
    except Exception as e:
        await message.reply(f"❌ Unpin failed: {str(e)}")

@app.on_message(filters.command("settitle") & filters.group)
async def set_title(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /settitle <new title>")
        return
    title = " ".join(message.command[1:])
    try:
        await client.set_chat_title(message.chat.id, title)
        await message.reply(f"✅ Title updated to: {title}")
    except Exception as e:
        await message.reply(f"❌ Title change failed: {str(e)}")

@app.on_message(filters.command("setphoto") & filters.group)
async def set_photo(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply("⚠️ Reply to a photo to set as group photo.")
        return
    try:
        photo = await client.download_media(message.reply_to_message.photo.file_id)
        await client.set_chat_photo(message.chat.id, photo)
        await message.reply("✅ Group photo updated!")
    except Exception as e:
        await message.reply(f"❌ Failed to set photo: {str(e)}")

@app.on_message(filters.command("setdescription") & filters.group)
async def set_description(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /setdescription <text>")
        return
    desc = " ".join(message.command[1:])
    try:
        await client.set_chat_description(message.chat.id, desc)
        await message.reply("✅ Group description updated!")
    except Exception as e:
        await message.reply(f"❌ Failed to set description: {str(e)}")

@app.on_message(filters.command("promote") & filters.group)
async def promote_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_manage_topics=True
            )
        )
        await message.reply(f"👑 Promoted {user_mention(target)} to admin!")
    except Exception as e:
        await message.reply(f"❌ Promote failed: {str(e)}")

@app.on_message(filters.command("demote") & filters.group)
async def demote_user(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    target = await resolve_user(client, message)
    if not target:
        await message.reply("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await client.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=ChatPrivileges()
        )
        await message.reply(f"👑 Demoted {user_mention(target)} from admin!")
    except Exception as e:
        await message.reply(f"❌ Demote failed: {str(e)}")

# --- GROUP FEATURES ---

@app.on_message(filters.command("setrules") & filters.group)
async def set_rules(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /setrules <text>")
        return
    global rules_text
    rules_text = " ".join(message.command[1:])
    await message.reply("✅ Rules updated!")

@app.on_message(filters.command("rules") & filters.group)
async def show_rules(_, message: Message):
    await message.reply(rules_text)

@app.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome(client, message: Message):
    if not await check_admin_and_reply(client, message):
        return
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /setwelcome <message>\nUse {mention} and {title} as placeholders.")
        return
    global welcome_message
    welcome_message = " ".join(message.command[1:])
    await message.reply("✅ Welcome message updated!")

@app.on_message(filters.command("welcome") & filters.group)
async def show_welcome(_, message: Message):
    await message.reply(welcome_message.replace("{mention}", "USER").replace("{title}", message.chat.title))

@app.on_message(filters.new_chat_members & filters.group)
async def welcome_new_member(client, message: Message):
    for user in message.new_chat_members:
        welcome_text = welcome_message.replace("{mention}", user.mention).replace("{title}", message.chat.title)
        await message.reply(welcome_text)

@app.on_message(filters.command("report") & filters.group)
async def report_user(client, message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ Reply to a message to report.")
        return
    admins = []
    async for member in client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot and member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
            admins.append(member.user.mention)
    if admins:
        admin_list = "\n".join(admins)
        report_msg = (
            f"🚨 **Report**\n"
            f"👤 Reporter: {message.from_user.mention}\n"
            f"⚠️ Reported message: [Link]({message.reply_to_message.link})\n"
            f"🛡 Admins notified:\n{admin_list}"
        )
        await message.reply(report_msg)
    else:
        await message.reply("ℹ️ No admins available to notify.")

@app.on_message(filters.command("staff") & filters.group)
async def show_staff(client, message: Message):
    admins = []
    async for member in client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot and member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
            admins.append(member.user.mention)
    if admins:
        await message.reply("👮 **Group Admins:**\n" + "\n".join(admins))
    else:
        await message.reply("ℹ️ No admins found.")

# --- UTILITIES ---

@app.on_message(filters.command("translate") & filters.group)
async def translate_text(_, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /translate <text>")
        return
    text = " ".join(message.command[1:])
    translator = Translator()
    try:
        translated = translator.translate(text, dest='en')
        await message.reply(f"🌐 Translation: {translated.text}")
    except Exception as e:
        await message.reply(f"❌ Translation failed: {str(e)}")

@app.on_message(filters.command("setnote") & filters.group)
async def set_note(client, message: Message):
    if len(message.command) < 3:
        await message.reply("⚠️ Usage: /setnote <name> <text>")
        return
    name = message.command[1]
    text = " ".join(message.command[2:])
    chat_id = message.chat.id
    notes.setdefault(chat_id, {})
    notes[chat_id][name] = text
    await message.reply(f"📝 Note `{name}` saved!")

@app.on_message(filters.command("getnote") & filters.group)
async def get_note(_, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /getnote <name>")
        return
    name = message.command[1]
    chat_id = message.chat.id
    if chat_id in notes and name in notes[chat_id]:
        await message.reply(notes[chat_id][name])
    else:
        await message.reply(f"⚠️ Note `{name}` not found.")

@app.on_message(filters.command("id"))
async def user_id(_, message: Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        await message.reply(f"🆔 Your ID: `{message.from_user.id}`")
    elif message.reply_to_message:
        user = message.reply_to_message.from_user
        await message.reply(f"👤 {user_mention(user)}'s ID: `{user.id}`", disable_web_page_preview=True)
    else:
        await message.reply(f"👤 Your ID: `{message.from_user.id}`\n💬 Chat ID: `{message.chat.id}`")

@app.on_message(filters.command("info") & filters.group)
async def user_info(client, message: Message):
    target = await resolve_user(client, message)
    if not target:
        target = message.from_user
    try:
        status = await client.get_chat_member(message.chat.id, target.id)
        joined_date = status.joined_date.strftime('%Y-%m-%d') if status.joined_date else "N/A"
        in_group = "Yes" if status.status != enums.ChatMemberStatus.BANNED else "No"
        info_text = (
            f"👤 **User Information**\n"
            f"🆔 ID: `{target.id}`\n"
            f"👤 Name: {target.first_name}\n"
            f"📛 Username: @{target.username if target.username else 'N/A'}\n"
            f"👥 In Group: {in_group}\n"
            f"🛡 Status: {status.status.name}\n"
            f"📅 Joined: {joined_date}"
        )
        await message.reply(info_text)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

# --- FUN COMMANDS ---

@app.on_message(filters.command("slap") & filters.group)
async def slap_user(_, message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        await message.reply(f"👋 {message.from_user.mention} slapped {target.mention} with a large trout! 🐟")
    else:
        await message.reply("⚠️ Reply to a user to slap.")

@app.on_message(filters.command("roll"))
async def roll_dice(_, message: Message):
    import random
    await message.reply(f"🎲 You rolled a {random.randint(1, 6)}!")

@app.on_message(filters.command("coin"))
async def flip_coin(_, message: Message):
    import random
    side = "Heads" if random.randint(0, 1) == 0 else "Tails"
    await message.reply(f"🪙 Coin flip: **{side}**")

@app.on_message(filters.command("say") & filters.group)
async def say_command(_, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /say <text>")
        return
    text = " ".join(message.command[1:])
    await message.reply(text)

# --- RUN BOT ---

if __name__ == "__main__":
    print("✅ Advanced Group Manager is running!")
    app.run()
