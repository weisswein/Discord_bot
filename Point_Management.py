import discord
from discord.ext import commands, tasks
from discord.ui import Modal, Button, View, TextInput
import asyncio
import os
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # messageの中身取得権限
intents.guilds = True
intents.members = True #メンバー情報の取得権限
YOUR_BOT_TOKEN=os.environ["BOT_TOKEN"]
bot = commands.Bot(command_prefix='/', intents=intents)


user_points = {}# ユーザーポイントを管理する辞書
user_report = {}# ユーザーの広告拡散回数
user_Admission = {}#許可待ちのユーザーによる運営の許可待ち判定
rejectmessage=str
# channel1 = bot.get_channel(1321015425202389097)#Bot起動確認チャンネル
# channel2 = bot.get_channel(1323241364384645160)#広告A
# channel3 = bot.get_channel(1323248333573328896)#広告B
# channel4 = bot.get_channel(1323248369237495829)#広告C
# channel5 = bot.get_channel(1323563327670063155)#報告A
# channel6 = bot.get_channel(1323563862473314305)#報告B
# channel7 = bot.get_channel(1323563912578469888)#報告C
# channel8 = bot.get_channel(1323245214319513631)#認証
# channel9 = bot.get_channel(1325967712006045736)#交流掲示板
# channel10 = bot.get_channel(1325970854793973900)#rankingBoards

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    channel1 = bot.get_channel(1321015425202389097)#Bot起動確認チャンネル
    # Replace with your channel ID
    for guild in bot.guilds:
        roles = guild.roles  # サーバー内のすべてのロールを取得
        role_names = [role.name for role in roles]  # ロール名のリストを作成
        print(f'Server: {guild.name} - Roles: {", ".join(role_names)}')
    print("Bot is ready!")
    role_A = discord.utils.get(channel1.guild.roles, name='7Point')
    role_B = discord.utils.get(channel1.guild.roles, name='課金者')
    role_C = discord.utils.get(channel1.guild.roles, name='運営')
    print(role_A,role_B,role_C)
    await channel1.send("Bot has started and is ready to go!")
    clear_boards.start()


#Discordボットのコマンド report を定義しています。
# このコマンドは、ユーザーが特定の掲示板（board）に投稿した証拠（proof）を報告するために使用されます。
# 以下は、このコマンドの機能の詳細です：
# コマンドの定義:
# @bot.command() デコレーターを使用して、report という名前のコマンドを定義しています。
# コマンドは ctx（コンテキスト）、board（掲示板の種類）、および proof（証拠）という3つの引数を取ります。
# ユーザーの取得:
# user = ctx.message.author でコマンドを実行したユーザーを取得します。
# ポイントの割り当て:
# board の値に応じて、ユーザーに割り当てるポイントを決定します。
# board が 'A' の場合、1ポイント。
# board が 'B' の場合、2ポイント。
# board が 'C' の場合、7ポイント。
# ユーザーポイントの管理:
# user_points という辞書を使用して、ユーザーのポイントを管理します。
# ユーザーが辞書に存在しない場合、新しいエントリを作成し、ポイントを初期化します。
# ユーザーのポイントを更新します。
# メッセージの送信:
# await ctx.send() を使用して、ユーザーにポイントが付与されたことを通知するメッセージを送信します。
# メッセージには、ユーザーのメンション、付与されたポイント、掲示板の種類、および合計ポイントが含まれます。
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # ボット自身のメッセージは無視する

    print(f'Message from {message.author}: {message.content}')
    await bot.process_commands(message)  # コマンドの処理を続行する

class MyModal(Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
       
        self.add_item(TextInput(
            label="Paragraph Input", style=discord.TextStyle.paragraph
        ))

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="送信内容")
        embed.add_field(name="Paragraph Input", value=self.children[0].value)
        await interaction.response.send_message(embeds=[embed])



class ApprovalView(View):
    def __init__(self, channel,user,message_link,points,report_message):
        super().__init__(timeout=None)
        self.user = channel#認証チャンネル
        self.user2= user#報告したユーザー
        self.message_link=message_link#報告されたメッセージのリンク
        self.points=points#付与予定のポイント
        self.report_message=report_message#認証で報告されたメッセージ

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_Admission[self.user2] = True
        user_points[self.user2] += self.points#Pointの加算
        await interaction.response.send_message(f'{self.user2.mention}様は{self.points} Points獲得.')
        await self.user2.send(f'掲載リンクの認証が通りました．{self.points} Points獲得です.合計：{user_points[self.user2]}\n掲載リンク:{self.message_link}')
        await self.report_message.delete()
        self.disable_buttons()
        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MyModal(title="却下された理由")
        await interaction.response.send_modal(modal)
        await self.user2.send(f'掲載リンクの認証が通りませんでした．詳しくは運営にご相談ください．\n掲載リンク:{self.message_link}')
        await self.report_message.delete()
        self.disable_buttons()
        self.stop()
    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

@bot.command(name='report', description='報告を以下のようにしてください。：/report')
async def report(ctx, board: str, proof: str):
    channel8 = bot.get_channel(1323245214319513631)#認証 
    message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
    user = ctx.message.author#コマンド入力したユーザー
    print(user)

    points = 0
    if board == 'A':
        points = 1
    elif board == 'B':
        points = 2 
    elif board == 'C':
        points = 7
    
    if user not in user_points:
        user_points[user] = 0
        user_Admission[user] = False

    await user.send(f'ご協力ありがとうございます．運営が確認を致しますので少々お待ちください．認証され次第,ポイントが加算されたことを通知します．\n掲載リンク:{message_link}')
    #↑報告したらDMに連絡．そして↓認証チャンネルにて報告
    view = ApprovalView(channel8,user,message_link,points,None)  # 一時的にNoneを設定
    report_message = await channel8.send(f"協力報告を頂きました．ご確認お願いします．\nuser:{user}\n認証:{message_link}",view=view)
    view.report_message=report_message#その後report_messageの追加
    
        # if user_points[user]>=7:
    #     await user.send(f'{user.mention} has been awarded {points} points for sharing on board {board}.'\
    #         f' Total points: {user_points[user]}\n'\
    #         'You can Send to board AB one time.\n'\
    #         '1.シェアして欲しい情報のURL\n'\
    #         '2.どのようにシェアをして欲しいか',ephemeral=True)
    #     #7PointRoleの追加
    #     role7 = discord.utils.get(ctx.guild.roles, name='7Point')
    #     await user.add_roles(role7)
    #     user_points[user]=user_points[user]-7
    # else:    
    
        # user.mention} has been awarded {points} points for sharing on board {board}.'\
        #      f' Total points: {user_points[user]}\n')

@tasks.loop(hours=168)  # 1週間ごとに実行
async def clear_boards():
    # 掲示板ABの内容を消去する処理
    pass

bot.run(YOUR_BOT_TOKEN)  # Replace with your bot token