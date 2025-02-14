import traceback

import nextcord, io
from nextcord.ext import commands
from openai import AsyncClient


class TestModelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.openai = AsyncClient(
            api_key="shard-ctuGdPZPGPDspcFWbKGGWTEpm6JUMwb1p",
            base_url="https://api.shard-ai.xyz/v1/",
        )

    @nextcord.slash_command(name="testmodel", description="Tests a model from the API.")
    async def testModel(
        self,
        interaction: nextcord.Interaction,
        model: str = nextcord.SlashOption(
            description="The model to test.", required=True
        ),
        prompt: str = nextcord.SlashOption(
            description="The prompt to use.", required=True
        ),
    ):
        await interaction.response.defer()
        try:

            response = await self.openai.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            response = response.choices[0].message.content
            if len(response) > 1999:
                file = nextcord.File(io.BytesIO(response.encode()), filename="response.txt")
                return await interaction.followup.send(file=file)
            else:
                embed = nextcord.Embed(
                    title="Success",
                    description=f"```{response}```",
                    color=nextcord.Color.dark_blue(),
                )
                embed.set_footer(
                    text="ShardAI - Free OpenAI reverse proxy",
                    icon_url="https://cdn.discordapp.com/avatars/1203571884218781696/85b6d76207bb80a8f7377ae693f93e1f.webp?size=4096",
                )
                return await interaction.followup.send(embed=embed)
        except Exception as e:
            print(str(e))
            return await self.send_error_response(
                interaction, "An error occurred while processing your request."
            )

    @nextcord.slash_command(
        name="testimage", description="Tests an image model from the API."
    )
    async def testImageModel(
        self,
        interaction: nextcord.Interaction,
        model: str = nextcord.SlashOption(
            description="The model to test.", required=True
        ),
        prompt: str = nextcord.SlashOption(
            description="The prompt for the image.", required=True
        ),
    ):
        await interaction.response.defer()
        try:


            response = await self.openai.images.generate(model=model, prompt=prompt)
            embed = nextcord.Embed(
                title="Success",
                color=nextcord.Color.dark_blue(),
            )
            embed.set_image(url=response.data[0].url)
            embed.set_footer(
                text="ShardAI - Free OpenAI reverse proxy",
                icon_url="https://cdn.discordapp.com/avatars/1203571884218781696/85b6d76207bb80a8f7377ae693f93e1f.webp?size=4096",
            )
            return await interaction.followup.send(embed=embed)
        except Exception as e:
            print(traceback.format_exc())
            return await self.send_error_response(
                interaction, "An error occurred while processing your request."
            )

    @nextcord.slash_command(
        name="testaudio", description="Tests an audio model from the API."
    )
    async def testAudioModel(
        self,
        interaction: nextcord.Interaction,
        model: str = nextcord.SlashOption(
            description="The model to test.", required=True
        ),
        prompt: str = nextcord.SlashOption(
            description="The prompt for the audio.", required=True
        ),
        voice: str = nextcord.SlashOption(
            description="The voice to use.", required=False
        ),
    ):
        await interaction.response.defer()
        try:

            response = await self.openai.audio.speech.create(
                model=model, input=prompt, voice=voice
            )
            embed = nextcord.Embed(
                title="Success",
                color=nextcord.Color.dark_blue(),
            )
            embed.set_footer(
                text="ShardAI - Free OpenAI reverse proxy",
                icon_url="https://cdn.discordapp.com/avatars/1203571884218781696/85b6d76207bb80a8f7377ae693f93e1f.webp?size=4096",
            )
            return await interaction.followup.send(
                embed=embed, file=nextcord.File(io.BytesIO(response.read()), "audio.mp3")
            )
        except Exception as e:
            print(traceback.format_exc())
            return await self.send_error_response(
                interaction, "An error occurred while processing your request."
            )

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
        return await interaction.followup.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(TestModelCog(bot))
    print("[!] The 'testmodel' command cog was loaded successfully!")
