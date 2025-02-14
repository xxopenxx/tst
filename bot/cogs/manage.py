from dataclasses import dataclass
from typing import Dict, Any, List

from nextcord import ui, ButtonStyle, Color, Embed, Interaction, Member, Permissions
from nextcord.ext import commands
import nextcord
import aiohttp

import sys
sys.path.append("..")
from api.config import bot_data

@dataclass
class BotData:
    token: str
    banner_url: str
    pfp_url: str
    pfp_transparent_url: str

API_BASE_URL: str = "https://api.shard-ai.xyz/v1/admin"
HEADERS: Dict[str, str] = {"Authorization": "Bearer &czot4$*,WRl7VG/+eXKd9LI1h?8n>yE"}
BRAND_COLOR: int = 0x1a237e
VERIFICATION_ROLE_ID = 1221342193713680394
ADMIN_USER_IDS = [1065714439380271164, 1133382299149402217, 659166266711605249]
 
class APIEndpoints:
    CHECK: str = f"{API_BASE_URL}/check"
    REGISTER: str = f"{API_BASE_URL}/register"
    RESET: str = f"{API_BASE_URL}/reset"
    USAGE: str = f"{API_BASE_URL}/usage"
    PLAN: str = f"{API_BASE_URL}/subscription"
    DELETE_KEY: str = f"{API_BASE_URL}/delete"
    ADD_KEY: str = f"{API_BASE_URL}/add"

class APIClient:
    def __init__(self, headers: Dict[str, str]) -> None:
        self.headers = headers

    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                return await response.json()

    async def check_key(self, user_id: int) -> Dict[str, Any]:
        return await self._make_request(APIEndpoints.CHECK, {"id": str(user_id)})

    async def register_key(self, user_id: int) -> Dict[str, Any]:
        return await self._make_request(APIEndpoints.REGISTER, {"id": str(user_id)})

    async def reset_key(self, user_id: int) -> Dict[str, Any]:
        return await self._make_request(APIEndpoints.RESET, {"id": str(user_id)})
    
    async def delete_key(self, user_id: int, key: str) -> Dict[str, Any]:
       return await self._make_request(APIEndpoints.DELETE_KEY, {"id": str(user_id), "key": key})

    async def get_usage(self, user_id: int) -> Dict[str, Any]:
        return await self._make_request(APIEndpoints.USAGE, {"id": str(user_id)})

    async def get_plan_details(self, user_id: int) -> Dict[str, Any]:
        return await self._make_request(APIEndpoints.PLAN, {"id": str(user_id)})
    
    async def add_key(self, user_id: int, name: str, description: str = None) -> Dict[str, Any]:
        payload = {"id": str(user_id), "name": name}
        if description:
            payload["description"] = description
        return await self._make_request(APIEndpoints.ADD_KEY, payload)

class BaseView(ui.View):
    def __init__(self, bot_data: BotData) -> None:
        super().__init__()
        self.bot_data = bot_data

    def get_base_embed(self, pfp: bool = True) -> Embed:
        embed = Embed(color=Color(BRAND_COLOR))
        if pfp:
            embed.set_thumbnail(url=self.bot_data.pfp_url)
        return embed

class DashboardView(BaseView):
    def __init__(self, api_client: APIClient, bot_data: BotData, user_id: int, user_name: str) -> None:
        super().__init__(bot_data)
        self.api_client = api_client
        self.user_id = user_id
        self.user_name = user_name

    def get_main_embed(self) -> Embed:
        embed = self.get_base_embed(pfp=False)
        embed.title = f"Dashboard for {self.user_name} ⚙️"
        embed.description = "Manage your API keys, usage, and subscription settings. ⚙️"
        return embed

    async def _check_verification(self, interaction: Interaction) -> bool:
         if not self._is_verified(interaction):
             await self._respond_with_error(
                 interaction,
                 "Please verify yourself to get your key."
            )
             return False
         return True

    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = self.get_base_embed(pfp=False)
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @ui.button(label="Keys 🔑", style=ButtonStyle.primary)
    async def keys(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        embed = self.get_base_embed()
        embed.title = "API Keys 🔑"
        try:
            response = await self.api_client.check_key(self.user_id)
            keys = response['key']
            if keys:
                for i, key in enumerate(keys):
                    embed.add_field(name=f"Key {i + 1}", value=f"Key: ||{key['key']}||", inline=True)
            else:
                embed.description = "You don't have any API keys. Create one below. 👇"

            view = KeysView(self.api_client, self.bot_data, self.user_id, self.user_name)
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=view)
        except Exception as e:
            embed.description = f"Error retrieving keys: {str(e)} ⚠️"
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=self)

    @ui.button(label="Usage 📈", style=ButtonStyle.primary)
    async def usage(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        embed = self.get_base_embed()
        embed.title = "Usage Statistics 📈"
        try:
            response = await self.api_client.get_usage(self.user_id)
            usage_data = response['usage']
            embed.add_field(name="Requests ⚙️", value=str(usage_data['usage']), inline=True)
            embed.add_field(name="Credits 💰", value=str(usage_data['credits']), inline=True)
            embed.add_field(name="Input Tokens ➡️", value=str(usage_data['tokens']['input']), inline=True)
            embed.add_field(name="Output Tokens ⬅️", value=str(usage_data['tokens']['output']), inline=True)
            view = UsageView(self.api_client, self.bot_data, self.user_id, self.user_name)
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=view)
        except Exception as e:
            embed.description = f"Error retrieving usage: {str(e)} ⚠️"
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=self)


    @ui.button(label="Plan 🧾", style=ButtonStyle.primary)
    async def plan(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        embed = self.get_base_embed()
        embed.title = "Subscription Plan 🧾"
        try:
            response = await self.api_client.get_plan_details(self.user_id)
            plan_data = response['subscription']
            embed.add_field(name="Type 🏷️", value=plan_data['type'].capitalize(), inline=True)
            embed.add_field(name="Credit Limit 💰", value=str(plan_data['credit_limit']), inline=True)
            embed.add_field(name="Rate Limit ⏱️", value=str(plan_data['rate_limit']), inline=True)
            view = PlanView(self.api_client, self.bot_data, self.user_id, self.user_name)
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=view)
        except Exception as e:
            embed.description = f"Error retrieving plan: {str(e)} ⚠️"
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=self)

class KeysView(BaseView):
    def __init__(self, api_client: APIClient, bot_data: BotData, user_id: int, user_name: str) -> None:
        super().__init__(bot_data)
        self.api_client = api_client
        self.user_id = user_id
        self.user_name = user_name

    async def _check_verification(self, interaction: Interaction) -> bool:
         if not self._is_verified(interaction):
             await self._respond_with_error(
                 interaction,
                 "Please verify yourself to get your key."
            )
             return False
         return True

    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = self.get_base_embed(pfp=False)
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @ui.button(label="Back ↩️", style=ButtonStyle.danger, row=0)
    async def back(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        view = DashboardView(self.api_client, self.bot_data, self.user_id, self.user_name)
        banner_embed = Embed(color=Color(BRAND_COLOR))
        banner_embed.set_image(url=self.bot_data.banner_url)
        banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
        await interaction.response.edit_message(embeds=[banner_embed, view.get_main_embed()], view=view)

    @ui.button(label="Create Key ➕", style=ButtonStyle.success, row=1)
    async def create_key(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        modal = CreateKeyModal(self.api_client, self.bot_data, self.user_id, self.user_name)
        await interaction.response.send_modal(modal)

    @ui.button(label="Delete Key 🗑️", style=ButtonStyle.secondary, row=1)
    async def delete_key(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        modal = DeleteKeyModal(self.api_client, self.user_id, self.bot_data, self.user_name)
        await interaction.response.send_modal(modal)

class UsageView(BaseView):
    def __init__(self, api_client: APIClient, bot_data: BotData, user_id: int, user_name: str) -> None:
        super().__init__(bot_data)
        self.api_client = api_client
        self.user_id = user_id
        self.user_name = user_name

    async def _check_verification(self, interaction: Interaction) -> bool:
         if not self._is_verified(interaction):
             await self._respond_with_error(
                 interaction,
                 "Please verify yourself to get your key."
            )
             return False
         return True

    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = self.get_base_embed(pfp=False)
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Back ↩️", style=ButtonStyle.danger)
    async def back(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        view = DashboardView(self.api_client, self.bot_data, self.user_id, self.user_name)
        banner_embed = Embed(color=Color(BRAND_COLOR))
        banner_embed.set_image(url=self.bot_data.banner_url)
        banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
        await interaction.response.edit_message(embeds=[banner_embed, view.get_main_embed()], view=view)

class PlanView(BaseView):
    def __init__(self, api_client: APIClient, bot_data: BotData, user_id: int, user_name: str) -> None:
        super().__init__(bot_data)
        self.api_client = api_client
        self.user_id = user_id
        self.user_name = user_name

    async def _check_verification(self, interaction: Interaction) -> bool:
         if not self._is_verified(interaction):
             await self._respond_with_error(
                 interaction,
                 "Please verify yourself to get your key."
            )
             return False
         return True

    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = self.get_base_embed(pfp=False)
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Back ↩️", style=ButtonStyle.danger)
    async def back(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        view = DashboardView(self.api_client, self.bot_data, self.user_id, self.user_name)
        banner_embed = Embed(color=Color(BRAND_COLOR))
        banner_embed.set_image(url=self.bot_data.banner_url)
        banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
        await interaction.response.edit_message(embeds=[banner_embed, view.get_main_embed()], view=view)

class CreateKeyModal(ui.Modal):
    def __init__(self, api_client: APIClient, bot_data: BotData, user_id: int, user_name: str) -> None:
        super().__init__(title="Create New API Key 🔑")
        self.api_client = api_client
        self.bot_data = bot_data
        self.user_id = user_id
        self.user_name = user_name
        self.key_name = ui.TextInput(
            label="Key Name",
            placeholder="Enter a name for the key",
            required=True,
            min_length=1,
            max_length=50
        )
        self.key_description = ui.TextInput(
            label="Key Description (Optional)",
            placeholder="Enter a description for the key",
            required=False,
            max_length=100,
        )
        self.add_item(self.key_name)
        self.add_item(self.key_description)

    async def callback(self, interaction: Interaction) -> None:
        try:
            response = await self.api_client.add_key(self.user_id, self.key_name.value, self.key_description.value if self.key_description.value else None)
            
            # fetch updated key list and make embed
            key_check_response = await self.api_client.check_key(self.user_id)
            keys = key_check_response.get('key', [])

            embed = Embed(title="API Keys 🔑", color=Color(BRAND_COLOR))
            if keys:
                for i, key in enumerate(keys):
                     embed.add_field(name=f"Key {i + 1}", value=f"Key: ||{key['key']}||", inline=True)
                embed.description = "Successfully created your new API Key. ✅"
            else:
                embed.description = "You don't have any API keys. Create one below. 👇"


            view = KeysView(self.api_client, self.bot_data, self.user_id, self.user_name)
            banner_embed = Embed(color=Color(BRAND_COLOR))
            banner_embed.set_image(url=self.bot_data.banner_url)
            banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
            await interaction.response.edit_message(embeds=[banner_embed, embed], view=view)

        except Exception as e:
            await interaction.response.send_message(f"Error creating key: {str(e)} ⚠️", ephemeral=True)

class RegisterView(BaseView):
    def __init__(self, api_client: APIClient, bot_data: BotData) -> None:
        super().__init__(bot_data)
        self.api_client = api_client

    async def _check_verification(self, interaction: Interaction) -> bool:
         if not self._is_verified(interaction):
             await self._respond_with_error(
                 interaction,
                 "Please verify yourself to get your key."
            )
             return False
         return True

    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = self.get_base_embed(pfp=False)
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Register ✅", style=ButtonStyle.success)
    async def register(self, button: ui.Button, interaction: Interaction) -> None:
        if not await self._check_verification(interaction):
            return
        try:
            register_response = await self.api_client.register_key(interaction.user.id)
            if register_response['success']:
                 # directly show the dashboard
                view = DashboardView(self.api_client, self.bot_data, interaction.user.id, interaction.user.name)
                banner_embed = Embed(color=Color(BRAND_COLOR))
                banner_embed.set_image(url=self.bot_data.banner_url)
                main_embed = view.get_main_embed()
                await interaction.response.edit_message(embeds=[banner_embed, main_embed], view=view)

            else:
                embed = self.get_base_embed()
                embed.title = "Registration Failed ⚠️"
                embed.description = f"An error occurred while registering you: {register_response.get('error', 'Unknown error')}"

                await interaction.response.edit_message(embed=embed, view=None)
        except Exception as e:
           embed = self.get_base_embed()
           embed.title = "Registration Failed ⚠️"
           embed.description = f"An error occurred while registering you: {str(e)}"
           await interaction.response.edit_message(embed=embed, view=None)
           
class DeleteKeyModal(ui.Modal):
    def __init__(self, api_client: APIClient, user_id: int, bot_data: BotData, user_name: str) -> None:
        super().__init__(title="Delete API Key 🗑️")
        self.api_client = api_client
        self.user_id = user_id
        self.bot_data = bot_data
        self.user_name = user_name
        self.key_input = ui.TextInput(
            label="Key Number",
            placeholder="Enter the key number to delete (e.g., 1 for Key 1)",
            required=True,
            min_length=1,
            max_length=2,
        )
        self.add_item(self.key_input)

    async def callback(self, interaction: Interaction) -> None:
        try:
            key_number = int(self.key_input.value) - 1
            response = await self.api_client.check_key(self.user_id)
            keys = response.get('key', [])

            if not keys:
                await interaction.response.send_message(f"No keys to delete. ⚠️", ephemeral=True)
                return
            if 0 <= key_number < len(keys):
                key_to_delete = keys[key_number]['key']
                response = await self.api_client.delete_key(self.user_id, key_to_delete)
                
                if response['success'] == True:
                     # Fetch updated key list and make embed
                    key_check_response = await self.api_client.check_key(interaction.user.id)
                    updated_keys = key_check_response.get('key', [])

                    embed = Embed(title="API Keys 🔑", color=Color(BRAND_COLOR))
                    if updated_keys:
                        for i, key in enumerate(updated_keys):
                            embed.add_field(name=f"Key {i + 1}", value=f"Key: ||{key['key']}||", inline=True)
                        embed.description = f"Successfully deleted key. ✅"
                    else:
                        embed.description = "You don't have any API keys. Create one below. 👇"
                    
                    view = KeysView(self.api_client, self.bot_data, self.user_id, self.user_name)
                    banner_embed = Embed(color=Color(BRAND_COLOR))
                    banner_embed.set_image(url=self.bot_data.banner_url)
                    banner_embed.title = f"Welcome to the Shard AI Dashboard for {self.user_name} ⚙️"
                    await interaction.response.edit_message(embeds=[banner_embed, embed], view=view)
                else:
                   await interaction.response.send_message(f"Error deleting key: Key not found ⚠️", ephemeral=True)
            else:
                await interaction.response.send_message(f"Invalid key number. ⚠️", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)} ⚠️", ephemeral=True)

class ManageDashboardAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot, bot_data: BotData) -> None:
        self.bot = bot
        self.bot_data = bot_data
        self.api_client = APIClient(HEADERS)

    def get_banner_embed(self, user_name: str = None) -> Embed:
        embed = Embed(color=Color(BRAND_COLOR))
        if user_name:
            embed.title = f"Welcome to the Shard AI Dashboard for {user_name} ⚙️"
        else:
            embed.title = "Welcome to the Shard AI Dashboard ⚙️"    
        embed.set_image(url=self.bot_data.banner_url)
        return embed
    
    def _is_verified(self, interaction: nextcord.Interaction) -> bool:
        """Check if the user has the verification role."""
        role = interaction.guild.get_role(VERIFICATION_ROLE_ID)
        return role in interaction.user.roles
    
    async def _respond_with_error(self, interaction: Interaction, message: str) -> None:
            embed = Embed(color=Color(BRAND_COLOR))
            embed.title = "Verification Error ⚠️"
            embed.description = message
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="manage", description="Open the Shard AI dashboard")
    async def dashboard(self, interaction: Interaction) -> None:
        if not self._is_verified(interaction):
            await self._respond_with_error(
                interaction,
                "Please verify yourself to get your key."
            )
            return
        try:
            check_response = await self.api_client.check_key(interaction.user.id)
            if check_response['key'][0] is None: # no user was found (havent created api key)
                
                embed = self.get_banner_embed()
                embed.title = "Welcome to Shard AI! 👋"
                embed.description = (
                    "Before you can access the dashboard, please read and agree to the Terms of Service:\n\n"
                    "**Terms of Service:**\n"
                    "> By using Shard's services you must agree that you will not abuse the service, that you will use it responsibly, and that you will follow the rules within the Discord.\n"
                    "If you agree, click the **'Register'** button below."
                )

                view = RegisterView(self.api_client, self.bot_data)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            elif check_response and check_response.get('success'):  #check for success first
                view = DashboardView(self.api_client, self.bot_data, interaction.user.id, interaction.user.name)
                banner_embed = self.get_banner_embed(interaction.user.name)
                main_embed = view.get_main_embed()
                await interaction.response.send_message(embeds=[banner_embed, main_embed], view=view, ephemeral=True)
            
            else:
                embed = Embed(title="Error", description="You are not registered. Please register with the bot to use the dashboard.", color=Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = Embed(title="Error", description=f"An error occurred: {str(e)}", color=Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="manage-admin", description="Open the Shard AI dashboard as any user")
    async def dashboard_admin(self, interaction: Interaction, member: Member) -> None:
        if interaction.user.id not in ADMIN_USER_IDS:
            embed = Embed(title="Error", description="You do not have permission to use this command.", color=Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not self._is_verified(interaction):
            await self._respond_with_error(
                interaction,
                "Please verify yourself to get your key."
            )
            return
        try:
            check_response = await self.api_client.check_key(member.id)
            if check_response['key'][0] is None:
                 embed = self.get_banner_embed(member.name)
                 embed.title = "Not Registered ⚠️"
                 embed.description = f"{member.name} has not yet registered. "
                 await interaction.response.send_message(embed=embed, ephemeral=True)
                 return
            if check_response and check_response.get('success'):
                 view = DashboardView(self.api_client, self.bot_data, member.id, member.name)
                 banner_embed = self.get_banner_embed(member.name)
                 main_embed = view.get_main_embed()
                 await interaction.response.send_message(embeds=[banner_embed, main_embed], view=view, ephemeral=True)
            
            else:
                embed = Embed(title="Error", description="You are not registered. Please register with the bot to use the dashboard.", color=Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = Embed(title="Error", description=f"An error occurred: {str(e)}", color=Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ManageDashboardAdmin(bot, bot_data))