import traceback
import nextcord
from nextcord.ext import commands
import ujson
from openai import AsyncClient
from nextcord.utils import escape_mentions

client: AsyncClient = AsyncClient(api_key="shard-ctuGdPZPGPDspcFWbKGGWTEpm6JUMwb1p", base_url="https://api.shard-ai.xyz/v1/")
messages: dict = {}

class ChatBotCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        with open("bot/cogs/chat.json", 'r') as f:
            data = ujson.load(f)
        if message.author.bot:
            return False
        if str(message.channel.id) in data:
            async with message.channel.typing():
                model = data[str(message.channel.id)]
                if message.author.id not in messages:
                    messages[message.author.id] = []
                
                if message.content.startswith('!clear'):
                    messages[message.author.id].clear()
                    await message.reply(content="History cleared.")
                elif message.content.startswith("!"):
                    pass
                else:
                    messages[message.author.id].append({'role': 'user', 'content': message.content})
                    
                    if len(messages[message.author.id]) > 15:
                        messages[message.author.id].pop(0)
                        
                    try:
                        response = await client.chat.completions.create(
                            model=model,
                            messages=messages[message.author.id],
                            stream=False
                        )
                        response = (response.choices[0].message.content)
                    except Exception as e:
                        print(f"Error: {e}")
                        await message.reply(content="Something went wrong.")
                        return
                    
                    if response:
                        messages[message.author.id].append({'role': 'assistant', 'content': response})
                        if len(response) > 1999:
                            chunks = [response[i:i+1999] for i in range(0, len(response), 1999)]
                            for chunk in chunks:
                                await message.reply(content=escape_mentions(chunk))
                        else:
                            await message.reply(content=escape_mentions(response))
                    else:
                        await message.reply(content="Something went wrong.")
        
    @nextcord.slash_command(name="chat-bot-setup", description="Sets up a chatbot channel, admin only.")
    async def setup_chat_bot(self, interaction: nextcord.Interaction, model: str = nextcord.SlashOption(description="Which model to use", required=True), name: str = nextcord.SlashOption(description="What to name the channel")):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(embed=nextcord.Embed(title="Uh oh!", description="You are missing required permissions to use this command!", color=nextcord.Color.red()))
            return
        
        category = interaction.guild.get_channel(1250466793185611807)  # ai category 
        
        if category:
            chat_channel = await category.create_text_channel(name)
            with open("bot/cogs/chat.json", 'r') as f:
                data = ujson.load(f)
            data[str(chat_channel.id)] = model
            with open("bot/cogs/chat.json", 'w') as f:
                ujson.dump(data, f, indent=4)
            
            await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="Success",
                    description=f"Successfully created a chatbot channel for {model} in {chat_channel.mention}",
                    color=nextcord.Color.dark_blue()
                )
            )

def setup(bot):
    bot.add_cog(ChatBotCog(bot))
    print("[!] The 'chat' command cog was uploaded successfully!")