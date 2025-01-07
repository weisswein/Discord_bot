import discord
from discord.ext import commands, tasks
from discord.ui import Modal, Button, View, TextInput
from datetime import datetime, timedelta
import os
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # messageの中身取得権限
intents.guilds = True
intents.members = True  # メンバー情報の取得権限
intents.voice_states = True  # VC接続時間を取得するための権限
YOUR_BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = commands.Bot(command_prefix='/', intents=intents)

user_points = {}  # ユーザーポイントを管理する辞書
user_shared={}
user_report = {}  # ユーザーの広告拡散回数
user_Admission = {}  # 許可待ちのユーザーによる運営の許可待ち判定
pending_approvals = {}  # 保留中の承認を管理する辞書
#交流掲示板
user_posts = {}#交流掲示板での投稿数
user_vc_time = {}#音声通話の時間
weekly_user_posts = {}#１週間の投稿数
weekly_user_vc_time = {}#１週間のVC時間
weekly_user_shares = {}#１週間のshare回数
join_time={}#VCの時間保管用
@bot.event
async def on_ready():
    global channel1,channel2,channel3,channel4,channel5,channel6,channel7,channel8,channel9,channel10,role_A,role_B,role_C,role_D
    channel1 = bot.get_channel(1321015425202389097)#Bot起動確認チャンネル
    channel2 = bot.get_channel(1323241364384645160)#広告A
    channel3 = bot.get_channel(1323248333573328896)#広告B
    channel4 = bot.get_channel(1323248369237495829)#広告C
    channel5 = bot.get_channel(1323563327670063155)#報告A
    channel6 = bot.get_channel(1323563862473314305)#報告B
    channel7 = bot.get_channel(1323563912578469888)#報告C
    channel8 = bot.get_channel(1323245214319513631)#認証
    channel9 = bot.get_channel(1325967712006045736)#交流掲示板
    channel10 = bot.get_channel(1325970854793973900)#rankingBoards
    print(f'Logged in as {bot.user}')
    for guild in bot.guilds:
        roles = guild.roles  # サーバー内のすべてのロールを取得
        role_names = [role.name for role in roles]  # ロール名のリストを作成
        print(f'Server: {guild.name} - Roles: {", ".join(role_names)}')
    print("Bot is ready!")
    role_A = discord.utils.get(channel1.guild.roles, name='7Point')
    role_B = discord.utils.get(channel1.guild.roles, name='課金者')
    role_C = discord.utils.get(channel1.guild.roles, name='運営')
    role_D = discord.utils.get(channel1.guild.roles, name='課金者用7point')
    print(role_A, role_B, role_C,role_D)
    await channel1.send("Bot has started and is ready to go!")
    clear_boards.start()
    check_pending_approvals.start()
    monthly_ranking.start()
    weekly_ranking.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # ボット自身のメッセージは無視する
    if isinstance(message.channel, discord.DMChannel):
        print(f'DM from {message.author}: {message.content}')
        await bot.process_commands(message)  # DMで受信したメッセージをコマンドとして処理する
    print(f'Message from {message.author}: {message.content}')
    
    # 書き込み回数をカウント
    if message.channel == channel9:
        user_posts[message.author] = user_posts.get(message.author, 0) + 1
        weekly_user_posts[message.author] = weekly_user_posts.get(message.author, 0) + 1
    elif message.channel == channel2:
        await message.author.remove_roles(role_A)
    elif message.channel == channel3:
        await message.author.remove_roles(role_D)   
    await bot.process_commands(message)  # コマンドの処理を続行する


#VCの接続時間
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        # ユーザーがVCに接続したとき
        user_vc_time[member] = user_vc_time.get(member, timedelta())
        weekly_user_vc_time[member] = weekly_user_vc_time.get(member, timedelta())
        print(f'{member}が入ってきた')
        join_time[member] = datetime.now()
        
    elif before.channel is not None and after.channel is None:
        # ユーザーがVCから切断したとき
        session_time = datetime.now() - join_time[member]
        user_vc_time[member] += session_time
        weekly_user_vc_time[member] += session_time
        print(f'{member}が出た{session_time}')


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
    def __init__(self, channel, user, message_link, points, report_message,shared_member):
        super().__init__(timeout=None)
        self.channel = channel  # 認証チャンネル
        self.user = user  # 報告したユーザー
        self.message_link = message_link  # 報告されたメッセージのリンク
        self.points = points  # 付与予定のポイント
        self.report_message = report_message  # 認証で報告されたメッセージ
        self.timestamp = datetime.now()  # 承認リクエストのタイムスタンプ
        self.shared_user = shared_member

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: Button):
        await self.approve(interaction)
        

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        modal = MyModal(self.user, self.message_link, title="却下された理由")
        await interaction.response.send_modal(modal)
        await self.user.send(f'掲載リンクの認証が通りませんでした．詳しくは運営にご相談ください．\n掲載リンク:{self.message_link}')
        # メッセージが存在するか確認してから削除
        try:
            await self.report_message.delete()
        except discord.errors.NotFound:
            print("メッセージが既に存在しないため、削除できませんでした。")
        self.disable_buttons()
        self.stop()

    async def approve(self, interaction=None):
        user_Admission[self.user] = True
        user_points[self.user] += self.points  # Pointの加算
        user_report[self.user] += 1 # 広告の拡散協力の回数加算
        user_shared[self.shared_user] += 1#シェアされた回数の加算
        weekly_user_shares[self.user] += 1#1週間ごとのシェア回数
        if interaction:
            await interaction.response.send_message(f'{self.user.mention}様は{self.points} Points獲得.')

        await self.user.send(f'掲載リンクの認証が通りました．{self.points} Points獲得です.合計：{user_points[self.user]}\n掲載リンク:{self.message_link}')
        # メッセージが存在するか確認してから削除
        try:
            await self.report_message.delete()

        except discord.errors.NotFound:
            print("メッセージが既に存在しないため、削除できませんでした。")
        self.disable_buttons()
        self.stop()

    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

@bot.command(name='report', description='報告を以下のようにしてください。：/report')
async def report(ctx, board: str,member: discord.Member = None, proof: str=None):
    if member is None:
        await ctx.send("ユーザー名を記載していないか、間違っています→例: /report A ユーザー名 URL")
        return
    elif(member==ctx.message.author ):
        await ctx.send("自分の広告はポイントに加算されません.\n他ユーザー名を入れてください")
        return
    if proof is None:
        await ctx.send("証拠が記載されていません")
        return  # デフォルトでコマンドを実行したユーザーを対象にする
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
        user_report[user] = 0
    if user not in weekly_user_shares:
        weekly_user_shares[user]=0
    if member not in user_shared:
        user_shared[member]=0
    await user.send(f'ご協力ありがとうございます．運営が確認を致しますので少々お待ちください．認証され次第,ポイントが加算されたことを通知します．\n掲載リンク:{message_link}')
    view = ApprovalView(channel8, user, message_link, points, None,member)  # 一時的にNoneを設定
    report_message = await channel8.send(f"協力報告を頂きました．ご確認お願いします．\nuser:{user}\n認証:{message_link}", view=view)
    view.report_message = report_message  # その後report_messageの追加
    pending_approvals[report_message.id] = view  # 保留中の承認に追加

@bot.command(name='pay7point')
async def pay7point(ctx):
    user = ctx.message.author  # コマンド入力したユーザー
    if user not in user_points:
        user_points[user] = 0
        user_Admission[user] = False
        
    if user_points[user] >= 7 and role_B not in user.roles:
        user_points[user] = user_points[user] - 7
        await user.add_roles(role_A)
    elif user_points[user] >= 7 and role_B in user.roles:
        user_points[user] = user_points[user] - 7
        await user.add_roles(role_D)
    else:
        await ctx.send(f'ポイントが7point以上無い為、支払いができません\n現在の合計:{user_points[user]}point')

@bot.command(name='userinfo', description='ユーザー情報を表示します。')
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.message.author  # デフォルトでコマンドを実行したユーザーを対象にする

    total_points = user_points.get(member, 0)
    current_points = user_points.get(member, 0)
    total_shares = user_report.get(member, 0)
    total_shared = user_shared.get(member, 0)

    embed = discord.Embed(title=f"{member.name}の情報", color=discord.Color.blue())
    embed.add_field(name="累計獲得ポイント数", value=total_points)
    embed.add_field(name="現在の保有ポイント数", value=current_points)
    embed.add_field(name="累計シェア回数", value=total_shares)
    embed.add_field(name="累計シェアされた回数", value=total_shared)
    await ctx.send(embed=embed)

@tasks.loop(minutes=1)  # 1分ごとに実行
async def check_pending_approvals():
    now = datetime.now()
    for message_id, view in list(pending_approvals.items()):
        if now - view.timestamp > timedelta(minutes=2):
            await view.approve()
            del pending_approvals[message_id]

@tasks.loop(minutes=1)  # 1時間ごとに実行
async def clear_boards():
    # 掲示板ABの内容を消去する処理
    channel2 = bot.get_channel(1323241364384645160)  # 広告A
    channel3 = bot.get_channel(1323248333573328896)  # 広告B
    # チャンネルのメッセージを削除
    await channel2.purge()
    await channel3.purge()





#rankingBoards
#【ランキングボードを月に一回】 
# ・これまでのシェアの回数 
# ・これまでの累計の書き込み回数（交流掲示板への書き込み回数） 
# ・これまでの累計のVC接続時間 
# 【ランキングボードを週に毎週月曜日朝9時】 
# ・前週のシェアの回数 ・前週の累計の書き込み回数（交流掲示板への書き込み回数） 
# ・前週の累計のVC接続時間

@tasks.loop(minutes=2)  # 毎日実行
async def monthly_ranking():
    #if datetime.now().day == 1:  # 月初めに実行
    print('実行された月間ランキング')
    embed = discord.Embed(title="月間ランキング", color=discord.Color.blue())
    embed.add_field(name="シェア回数", value=format_ranking(user_report))
    embed.add_field(name="書き込み回数", value=format_ranking(user_posts))
    embed.add_field(name="VC接続時間", value=format_ranking(user_vc_time, time_format=True))
    await channel10.send(embed=embed)

@tasks.loop(minutes=10)  # 1週間ごとに実行
async def weekly_ranking():
    #if datetime.now().weekday() == 0 and datetime.now().hour == 9:  # 毎週月曜日の朝9時に実行
    print('実行された週間ランキング')
    embed = discord.Embed(title="週間ランキング", color=discord.Color.green())
    embed.add_field(name="シェア回数", value=format_ranking(weekly_user_shares))
    embed.add_field(name="書き込み回数", value=format_ranking(weekly_user_posts))
    embed.add_field(name="VC接続時間", value=format_ranking(weekly_user_vc_time, time_format=True))
    await channel10.send(embed=embed)
    reset_weekly_data()

def format_ranking(data, time_format=False):
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    ranking = ""
    for i, (user, value) in enumerate(sorted_data, 1):
        if time_format:
            value = str(value)
        ranking += f"{i}. {user.name}: {value}\n"
    return ranking

def reset_weekly_data():
    global weekly_user_shares, weekly_user_posts, weekly_user_vc_time
    weekly_user_shares = {}
    weekly_user_posts = {}
    weekly_user_vc_time = {}




bot.run(YOUR_BOT_TOKEN)