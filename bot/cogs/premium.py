import traceback

import aiohttp
import nextcord
from nextcord.ext import commands
from ujson import dumps


class PremiumCog(commands.Cog):
    def __init__(self, bot: commands.Bot, headers: dict):
        self.bot = bot
        self.headers = headers

    @nextcord.slash_command(
        name="premium", description="Switches the premium status in a key."
    )
    async def premiumCommand(
        self,
        interaction: nextcord.Interaction,
        subscription: str = nextcord.SlashOption(
            description="The type of update to perform.", choices={
                "👑 Premium": "premium",
                "💎 Basic": "basic",
                "🆓 Free": "free",
                "🔥 Custom": 'custom'
            }, required=True
        ),
        user: nextcord.Member = nextcord.SlashOption(
            description="The user to switch the status of.", required=True
        ),
        rate_limit: int = nextcord.SlashOption(
            description="Custom rate limit",
            required=False
        ),
        credit_limit: int = nextcord.SlashOption(
            description="Custom credit limit",
            required=False
        )
    ):
        try:
            if not interaction.user.guild_permissions.administrator:
                return await self.send_error_response(
                    interaction, "You don't have permission to use this command."
                )

            async with aiohttp.ClientSession(json_serialize=dumps) as session:
                payload = {"id": str(user.id), 'premium': subscription, "credit_limit": credit_limit, "rate_limit": rate_limit}
                async with session.post(
                    f"https://api.shard-ai.xyz/v1/admin/update",
                    headers=self.headers,
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                       return await self.send_success_response(
                            interaction,
                            f'Switched the {subscription} status of this user.',
                        )
                    else:
                        error_data = await resp.json()
                        return await self.send_error_response(interaction, f"Error: {error_data.get('error', 'Unknown error')}")
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
    bot.add_cog(PremiumCog(bot, headers))
    print("[!] The 'premium' command cog was loaded successfully!")