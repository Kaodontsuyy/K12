import discord
from discord.ext import commands
import json
import os
import re
import asyncio

class ClaimsCog(commands.Cog):
    CLAIMS_FILE = "claims.json"

    def __init__(self, bot):
        self.bot = bot
        self.source_channel_id = 1411741169662300226
        self.dest_channel_id = 1421065710418788403
        self._claims = self._load_claims()
        self._lock = asyncio.Lock()

        self.emoji_basic = "<:nitrobasic:1421044066841399329>"
        self.emoji_boost = "<a:hgjhjgjhhj:1421043988940455969>"

    def _load_claims(self):
        if not os.path.exists(self.CLAIMS_FILE):
            with open(self.CLAIMS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}
        try:
            with open(self.CLAIMS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except Exception as e:
            print(f"[ClaimsCog] Lỗi load file: {e}")
            return {}

    def _save_claims(self):
        try:
            with open(self.CLAIMS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._claims, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ClaimsCog] Lỗi save file: {e}")

    async def _get_channel(self, cid):
        ch = self.bot.get_channel(cid)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(cid)
            except Exception as e:
                print(f"[ClaimsCog] Không fetch được channel {cid}: {e}")
                return None
        return ch

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            if message.channel.id != self.source_channel_id:
                return
        except:
            return
    
        async with self._lock:
            tracked = list(self._claims.items())
        if not tracked:
            return
    
        content = message.content or ""
        low = content.lower()
        if "successfully claimed" not in low:
            return
    
        mention_ids_in_msg = set(m.id for m in (message.mentions or []))
        found_targets = set()
        for tid, _ in tracked:
            if (
                tid in mention_ids_in_msg
                or f"<@{tid}>" in content
                or f"<@!{tid}>" in content
            ):
                found_targets.add(tid)
        if not found_targets:
            return
    
        if "nitro basic" in low:
            emoji = self.emoji_basic
        elif "nitro" in low:
            emoji = self.emoji_boost
        else:
            return
    
        # Remove role pings but keep emojis and other content
        sanitized = re.sub(r"<@&\d+>", "", content)  # Remove role mentions
        sanitized = sanitized.replace("@claim ping", "").strip()
        
        # Keep the original emojis in the message
        # Don't remove custom emojis like we did before
    
        m = re.search(r"\(``(\d+/\d+)``\)", sanitized)
        claim_str = m.group(1) if m else None
    
        dest = await self._get_channel(self.dest_channel_id)
        if not dest:
            return
    
        for tid in found_targets:
            async with self._lock:
                entry = self._claims.get(tid)
                if not entry:
                    continue
    
                stored = set(entry.get("claims", []))
                if claim_str and claim_str in stored:
                    continue
    
                # Send the form message with emoji but without role ping
                txt = f"{emoji} {sanitized}"
                try:
                    await dest.send(txt)
                except:
                    pass
    
                if claim_str:
                    stored.add(claim_str)
                    entry["claims"] = list(stored)
                    entry["progress"] = len(stored)
    
                target = entry.get("target", 0)
                if target and entry.get("progress", 0) >= target:
                    del self._claims[tid]
    
                self._save_claims()

    @commands.command(name="claims")
    async def claims(self, ctx, user: discord.Member, target: int):
        uid = str(user.id)
        if uid not in self._claims:
            self._claims[uid] = {"target": target, "progress": 0, "claims": []}
        else:
            self._claims[uid]["target"] = target
        self._save_claims()
        await ctx.send(f"✅ Đã thêm {user.mention} vào danh sách claim (mục tiêu {target}).")

    @commands.command(name="clearclaims")
    async def clearclaims(self, ctx, user: discord.Member):
        uid = str(user.id)
        if uid in self._claims:
            del self._claims[uid]
            self._save_claims()
            await ctx.send(f"🗑️ Đã xoá dữ liệu claims của {user.mention}.")