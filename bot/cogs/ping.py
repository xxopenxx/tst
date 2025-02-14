import traceback

import nextcord
from nextcord.ext import commands


class PingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(name="ping", description="Returns the bot's latency.")
    async def ping(self, interaction: nextcord.Interaction):
        try:
            embed = nextcord.Embed(
                title="Pong!",
                description=f"My ping is: {self.bot.latency * 1000:.2f} ms",
                color=nextcord.Color.from_rgb(r=47, g=255, b=0),
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(traceback.format_exc())
            embed = nextcord.Embed(
                title="Error", description=f"``{str(e)}``", colour=nextcord.Colour.red()
            )
            embed.set_footer(
                text="FreeGPT - AI chatbot",
                icon_url="https://cdn.discordapp.com/avatars/1179997484735533087/5337a0f0845861793079ba0797743acd",
            )
            await interaction.response.send_message(embed=embed)
            return


def setup(bot):
    bot.add_cog(PingCog(bot))
    print("[!] The 'ping' command cog was loaded successfully!")
