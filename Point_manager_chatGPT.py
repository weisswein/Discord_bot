import discord
from discord.ext import commands, tasks
from discord.ui import Modal, Button, View, TextInput
import asyncio
from datetime import datetime, timedelta
import os
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # messageの中身取得権限
intents.guilds = True
intents.members = True  # メンバー情報の取得権限
YOUR_BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = commands.Bot(command_prefix='/', intents=intents)

user_points = {}  # ユーザーポイントを管理する辞書
user_report = {}  # ユーザーの広告拡散回数
user_Admission = {}  # 許可待ちのユーザーによる運営の許可待ち判定
pending_approvals = {}  # 保留中の承認を管理する辞書

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    channel1 = bot.get_channel(1321015425202389097)  # Bot起動確認チャンネル
    for guild in bot.guilds:
        roles = guild.roles  # サーバー内のすべてのロールを取得
        role_names = [role.name for role in roles]  # ロール名のリストを作成
        print(f'Server: {guild.name} - Roles: {", ".join(role_names)}')
    print("Bot is ready!")
    role_A = discord.utils.get(channel1.guild.roles, name='7Point')
    role_B = discord.utils.get(channel1.guild.roles, name='課金者')
    role_C = discord.utils.get(channel1.guild.roles, name='運営')
    print(role_A, role_B, role_C)
    await channel1.send("Bot has started and is ready to go!")
    clear_boards.start()
    check_pending_approvals.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # ボット自身のメッセージは無視する
    if isinstance(message.channel, discord.DMChannel):
        print(f'DM from {message.author}: {message.content}')
        await bot.process_commands(message)  # DMで受信したメッセージをコマンドとして処理する

    print(f'Message from {message.author}: {message.content}')
    await bot.process_commands(message)  # コマンドの処理を続行する

class MyModal(Modal):
    def __init__(self, user, messageLink, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.rejectmessage = TextInput(
            label="Paragraph Input", style=discord.TextStyle.paragraph
        )
        self.add_item(self.rejectmessage)
        self.messageLink = messageLink

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            embed = discord.Embed(title="却下された理由")
            embed.add_field(name=f"報告リンク:{self.messageLink}", value=self.rejectmessage.value)
            await interaction.response.send_message(embeds=[embed])
            await self.user.send(embeds=[embed])
        except Exception as e:
            print(f"Error: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)

class ApprovalView(View):
    def __init__(self, channel, user, message_link, points, report_message):
        super().__init__(timeout=None)
        self.channel = channel  # 認証チャンネル
        self.user = user  # 報告したユーザー
        self.message_link = message_link  # 報告されたメッセージのリンク
        self.points = points  # 付与予定のポイント
        self.report_message = report_message  # 認証で報告されたメッセージ
        self.timestamp = datetime.now()  # 承認リクエストのタイムスタンプ

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.approve(interaction)
        await self.report_message.delete()
        self.disable_buttons()
        self.stop()


    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MyModal(self.user, self.message_link, title="却下された理由")
        await interaction.response.send_modal(modal)
        await self.user.send(f'掲載リンクの認証が通りませんでした．詳しくは運営にご相談ください．\n掲載リンク:{self.message_link}')
        await self.report_message.delete()
        self.disable_buttons()
        self.stop()

    async def approve(self, interaction=None):
        user_Admission[self.user] = True
        user_points[self.user] += self.points  # Pointの加算
        if interaction:
            await interaction.response.send_message(f'{self.user.mention}様は{self.points} Points獲得.')
        await self.user.send(f'掲載リンクの認証が通りました．{self.points} Points獲得です.合計：{user_points[self.user]}\n掲載リンク:{self.message_link}')
        await self.report_message.delete()
        self.disable_buttons()
        self.stop()

    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

@bot.command(name='report', description='報告を以下のようにしてください。：/report')
async def report(ctx, board: str, proof: str):
    channel8 = bot.get_channel(1323245214319513631)  # 認証
    channel5 = bot.get_channel(1323563327670063155)  # 報告A
    channel6 = bot.get_channel(1323563862473314305)  # 報告B
    channel7 = bot.get_channel(1323563912578469888)  # 報告C
    message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
    user = ctx.message.author  # コマンド入力したユーザー
    print(user)

    points = 0
    if board == 'A' and ctx.channel == channel5:
        points = 1
    elif board == 'B' and ctx.channel == channel6:
        points = 2
    elif board == 'C' and ctx.channel == channel7:
        points = 7
    else:
        await ctx.send("コマンドの表記と報告場所が異なります．\nA:無課金者広告の報告場所,B:課金者広告の報告場所,C:キャンペーン広告の報告場所でお願いいたします．", ephemeral=True)
        return
    if user not in user_points:
        user_points[user] = 0
        user_Admission[user] = False
    await user.send(f'ご協力ありがとうございます．運営が確認を致しますので少々お待ちください．認証され次第,ポイントが加算されたことを通知します．\n掲載リンク:{message_link}')
    view = ApprovalView(channel8, user, message_link, points, None)  # 一時的にNoneを設定
    report_message = await channel8.send(f"協力報告を頂きました．ご確認お願いします．\nuser:{user}\n認証:{message_link}", view=view)
    view.report_message = report_message  # その後report_messageの追加
    pending_approvals[report_message.id] = view  # 保留中の承認に追加

@bot.command(name='pay7point')
async def pay7point(ctx):
    user = ctx.message.author  # コマンド入力したユーザー
    role_A = discord.utils.get(ctx.guild.roles, name='7Point')
    if user not in user_points:
        user_points[user] = 0
        user_Admission[user] = False
        
    if user_points[user] >= 7:
        user_points[user] = user_points[user] - 7
        await user.add_roles(role_A)
    else:
        await ctx.send(f'ポイントが7point以上無い為、支払いができません\n現在の合計:{user_points[user]}point')

@tasks.loop(minutes=1)  # 1時間ごとに実行
async def check_pending_approvals():
    now = datetime.now()
    for message_id, view in list(pending_approvals.items()):
        if now - view.timestamp > timedelta(minutes=2):
            await view.approve()
            del pending_approvals[message_id]

@tasks.loop(hours=1)  # 1時間ごとに実行
async def clear_boards():
    # 掲示板ABの内容を消去する処理
    channel2 = bot.get_channel(1323241364384645160)#広告A
    channel3 = bot.get_channel(1323248333573328896)#広告B
    # チャンネルのメッセージを削除
    await channel2.purge()
    await channel3.purge()

bot.run(YOUR_BOT_TOKEN)