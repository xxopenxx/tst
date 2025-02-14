import traceback
import time
import nextcord
from nextcord.ext import commands
import ujson
from openai import AsyncClient
from nextcord.utils import escape_mentions
from collections import defaultdict

client = AsyncClient(
    api_key="shard-ctuGdPZPGPDspcFWbKGGWTEpm6JUMwb1p",
    base_url="https://api.shard-ai.xyz/v1/"
)

channel_histories = defaultdict(list)
user_histories = defaultdict(lambda: defaultdict(list))
user_request_times = defaultdict(list)
MESSAGE_EXPIRY = 180
MAX_HISTORY = 15

with open('data/bot/prompt.txt', 'r') as f:
    system_prompt = f.read()

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.bot:
            return
        
        if message.content.lower().startswith("shard") or self.bot.user in message.mentions:
            user_id = message.author.id
            current_time = time.time()
            
            user_request_times[user_id] = [t for t in user_request_times[user_id] if current_time - t < 60]
            if len(user_request_times[user_id]) >= 5:
                return

            user_request_times[user_id].append(current_time)
            await self.handle_chat(message)

    def cleanup_expired_messages(self, messages, current_time):
        return [msg for msg in messages if current_time - msg.get('timestamp', current_time) < MESSAGE_EXPIRY][-MAX_HISTORY:]

    async def handle_chat(self, message: nextcord.Message):
        async with message.channel.typing():
            current_time = time.time()
            channel_id = message.channel.id
            user_id = message.author.id

            channel_histories[channel_id] = self.cleanup_expired_messages(channel_histories[channel_id], current_time)
            user_histories[user_id] = self.cleanup_expired_messages(user_histories[user_id], current_time)

            messages = [{'role': 'system', 'content': system_prompt}]
            messages.extend(channel_histories[channel_id])
            messages.extend(user_histories[user_id])

            user_message = {'role': 'user', 'content': message.content, 'timestamp': current_time}
            messages.append(user_message)

            try:
                response = await client.chat.completions.create(
                    model="mistral-large-latest",
                    messages=messages,
                    stream=False
                )
                assistant_reply = response.choices[0].message.content
                assistant_message = {'role': 'assistant', 'content': assistant_reply, 'timestamp': current_time}

                channel_histories[channel_id].extend([user_message, assistant_message])
                user_histories[user_id].extend([user_message, assistant_message])

                if assistant_reply:
                    if len(assistant_reply) > 1999:
                        chunks = [assistant_reply[i:i+1999] for i in range(0, len(assistant_reply), 1999)]
                        for chunk in chunks:
                            await message.reply(content=escape_mentions(chunk))
                    else:
                        await message.reply(content=escape_mentions(assistant_reply))
                else:
                    await message.reply(content="I didn't get a response. Please try again.")
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()
                await message.reply(content="Something went wrong while processing your request.")

def setup(bot):
    bot.add_cog(SupportCog(bot))
    print("[!] The 'support' command cog was loaded successfully!")