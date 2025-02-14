import traceback

import aiohttp
import nextcord
from nextcord.ext import commands
from ujson import dumps


class BanCog(commands.Cog):
    def __init__(self, bot: commands.Bot, headers: dict):
        self.bot = bot
        self.headers = headers

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async with aiohttp.ClientSession(json_serialize=dumps) as session:
            payload = {"id": str(user.id), "banned": True}
            async with session.post(
                f"https://api.shard-ai.xyz/v1/admin/update",
                headers=self.headers,
                json=payload,
            ):
                pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        async with aiohttp.ClientSession(json_serialize=dumps) as session:
            payload = {"id": str(user.id), "banned": False}
            async with session.post(
                f"https://api.shard-ai.xyz/v1/admin/update",
                headers=self.headers,
                json=payload,
            ):
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with aiohttp.ClientSession(json_serialize=dumps) as session:
            payload = {"id": str(member.id), "banned": True}
            async with session.post(
                f"https://api.shard-ai.xyz/v1/admin/update",
                headers=self.headers,
                json=payload,
            ):
                pass

    @nextcord.slash_command(name="ban", description="Switches the ban status in a key.")
    async def banCommand(
        self,
        interaction: nextcord.Interaction,
        status: bool = nextcord.SlashOption(
            description="The ban status.", required=True
        ),
        user: nextcord.Member = nextcord.SlashOption(
            description="The user to switch the status of.", required=True
        ),
    ):
        try:
            if not interaction.user.guild_permissions.administrator:
                return await self.send_error_response(
                    interaction, "You don't have permission to use this command."
                )

            async with aiohttp.ClientSession(json_serialize=dumps) as session:
                payload = {"id": str(user.id), "banned": status}
                async with session.post(
                    f"https://api.shard-ai.xyz/v1/admin/update",
                    headers=self.headers,
                    json=payload,
                ) as _:
                    return await self.send_success_response(
                        interaction,
                        f'Switched the ban status of this user to: **{"true" if status else "false"}**',
                    )
        except Exception as e:
            print(traceback.format_exc())
            return await self.send_error_response(interaction, str(e))

    async def send_error_response(
        self, interaction: nextcord.Interaction, message: str
    ):
        embed = nextcord.Embed(
            title="Error", description=message, colour=nextcord.Colour.red()
        )
        return await self.send_embed_response(interaction, embed)

    async def send_success_response(
        self, interaction: nextcord.Interaction, message: str
    ):
        embed = nextcord.Embed(
            title="Done",
            description=message,
            color=nextcord.Color.from_rgb(r=47, g=255, b=0),
        )
        return await self.send_embed_response(interaction, embed)

    async def send_embed_response(
        self, interaction: nextcord.Interaction, embed: nextcord.Embed
    ):
        embed.set_footer(
            text="ShardAI - Free OpenAI reverse proxy",
            icon_url="https://cdn.discordapp.com/avatars/1203571884218781696/85b6d76207bb80a8f7377ae693f93e1f.webp?size=4096",
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    headers = {
        "Authorization": "Bearer &czot4$*,WRl7VG/+eXKd9LI1h?8n>yE"
    }
    bot.add_cog(BanCog(bot, headers))
    print("[!] The 'ban' command cog was loaded successfully!")
