import discord
from discord.ext import commands
import asyncio
import datetime

from player import Player

# .envからDISCORトークンとチャンネルIDを取得
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

# Botのインテント(イベントを監視する対象)を設定
### メッセージとリアクションに関するイベントのみをボットに許可
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 対局待ちとマッチリストを格納するためのキューを生成
queue = []
match_list = []

# 「!helpCommand」「!ヘルプ」と入力されたら、各コマンドの説明をEmbedメッセージで返す
@bot.command(aliases=['ヘルプ'])
async def helpCommand(ctx):
    embed = discord.Embed(title="Command Help", description="This program is a bot for recruiting people who want to play on Discord.", color=0x00ff00)
    embed.add_field(name="English commands", value="", inline=False)
    embed.add_field(name="!JoinMatch MonthDayHourMinute(ex.01252030…1/25 20:30)", value="Want to join a game? Use this command. The bot will ask you for a date.Enter the desired match time. If not specified, the Bot will ask for it.", inline=False)
    embed.add_field(name="!MatchQueue", value="Curious who's up for a game? This command shows you the list.", inline=False)
    embed.add_field(name="!ChooseMatch", value="Time to pick your opponent. Use this command.", inline=False)
    embed.add_field(name="!CancelMatch", value="Changed your mind? Cancel your match request with this command.", inline=False)
    embed.add_field(name="!ReservationStatus", value="Check your current reservations with this command.", inline=False)    
    embed.add_field(name="",  value="", inline=False)

    embed.add_field(name="ヘルプ",  value="このプログラムは、Discordで対局したい人を募集するためのBotです。", inline=False)
    embed.add_field(name="日本語コマンド",  value="", inline=False)
    embed.add_field(name="!対局したい 月日時分(例：01252030…1/25 20:30)", value="対局に参加したい時、このコマンドで申し込みます。時刻をスペース後に入力で指定できます。指定がない場合は次に日付を聞かれるので、入力してください。", inline=False)
    embed.add_field(name="!対局待ち", value="対局待ちの一覧を見たい時はこれ！", inline=False)
    embed.add_field(name="!マッチ選択", value="対局する相手を選ぶ時に使うよ。", inline=False)
    embed.add_field(name="!キャンセル", value="対局申し込みをキャンセルする時にはこちら。", inline=False)
    embed.add_field(name="!予約状況", value="予約済みの対局一覧を確認するためのコマンドです。", inline=False)

    await ctx.send(embed=embed)

# 対局待ちキューにプレイヤーを追加するための関数
def add_to_queue(player):
    queue.append(player)
    return True

# Botが準備ができた時に実行されるイベントハンドラ。ログを出力し、定期的なキュー更新を行うタスクを開始する
@bot.event
async def on_ready():
    print('ログインしました')
    bot.loop.create_task(periodic_queue_update())


# 「!対局したい」「!JoinMatch」と入力されたら、対局待ちリストにユーザを追加する処理
#### ユーザを対局待ちキューに追加し、確認メッセージを返す
@bot.command(aliases=['対局したい'])
async def JoinMatch(ctx, *, date=None):
    user = ctx.author

    def check_message(message):
        return message.author == ctx.author and message.channel == ctx.channel

    if not date:
        await ctx.send(f'{user.mention} \n希望の日時を入力してください月日時分(例：01252030…1/25 20:30).\n Please enter the desired date and timeMonth, date, hour, minute (e.g. 01252030...1/25 20:30)')
        try:
            msg = await bot.wait_for('message', check=check_message, timeout=60)
            date = msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send(f'{user.mention} 入力がタイムアウトしました。もう一度お試しください。')
            await ctx.send(f'{user.mention} input timed out. Please try again.')

    date = date.replace(" ", "")
    if len(date) != 8:
        await ctx.send(f'{user.mention} 日付の形式が正しくありません。もう一度お試しください。')
        await ctx.send(f'{user.mention} The date format is incorrect. Please try again.')
        return

    try:
        month = int(date[0:2])
        day = int(date[2:4])
        hour = int(date[4:6])
        minute = int(date[6:8])
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        if month == 1 and current_month == 12:
            current_year += 1
        game_time = datetime.datetime(current_year, month, day, hour, minute)
        if game_time > datetime.datetime.now():
            player = Player(user, game_time)
            add_to_queue(player)
            await ctx.send(f'{user.mention} が対局待ちリストに追加されました。')
            await ctx.send(f'{user.mention} has been added to the waiting list.')
        else:
            await ctx.send(f'{user.mention} 入力された日時は {game_time} です')
            await ctx.send('過去の日付になっています。\n' \
                           '!対局したい コマンドからやり直してください')
            await ctx.send(f'{user.mention} date entered is {game_time}')
            await ctx.send('The date is in the past. \n' \
                           'Please start over from the command !JoinMatch')
    except ValueError:
        await ctx.send(f'{user.mention} 日付の形式が正しくありません。もう一度お試しください。')
        await ctx.send(f'{user.mention} The date format is incorrect. Please try again.')

# 対局待ちキューをEmbedメッセージで表示するための関数
async def show_queue(channel):
    embed = discord.Embed(title="対局待ちリスト", color=0x00ff00)
    embed = discord.Embed(title="waiting list", color=0x00ff00)
    if len(queue) == 0:
        embed.add_field(name='', value='誰も対局待ちしていません。', inline=False)
        embed.add_field(name='', value='No one is waiting for a game.' , inline=False)
    else:
        embed.add_field(name='', value=f'No.', inline=True)
        embed.add_field(name='', value=f'User.', inline=True)
        embed.add_field(name='', value=f'Date.', inline=True)
        embed.add_field(name='', value=f'', inline=False)
        for i, q in enumerate(queue):
            embed.add_field(name='', value=f'{i + 1}.', inline=True)
            embed.add_field(name='', value=f'{q.user}', inline=True)
            embed.add_field(name='', value=f'{q.time}', inline=True)  
    await channel.send(embed=embed)

# 対局予約リストをEmbedメッセージで表示するための関数
async def show_match_list(channel):
    embed = discord.Embed(title="対局予約リスト", color=0x00ff00)
    embed = discord.Embed(title="Game reservation list", color=0x00ff00)
    if len(match_list) == 0:
        embed.add_field(name='', value='現在予約されている対局はありません。', inline=False)
        embed.add_field(name='', value='No games currently reserved.' , inline=False)
    else:
        embed.add_field(name='', value=f'No.', inline=True)
        embed.add_field(name='', value=f'User1.', inline=True)
        embed.add_field(name='', value=f'User2.', inline=True)
        embed.add_field(name='', value=f'Date.', inline=True)
        embed.add_field(name='', value=f'', inline=False)
        for i, q in enumerate(match_list):
            print(f'{q}')
            embed.add_field(name='', value=f'{i + 1}.', inline=True)
            embed.add_field(name='', value=f'{q["player1"]}', inline=True)
            embed.add_field(name='', value=f'{q["player2"]}', inline=True)
            embed.add_field(name='', value=f'{q["date"]}', inline=True)   
    await channel.send(embed=embed)

# '!対局待ち' や '!MatchQueue' コマンドを処理するための関数。対局待ちキューを表示する
@bot.command(aliases=['対局待ち'])
async def MatchQueue(ctx):
    await show_queue(ctx.channel)

#キャンセルまたは CancelMatchという名前の非同期関数を定義します。
##この関数はユーザーが待機中の対局をキャンセルするために使用します。
@bot.command(aliases=['キャンセル'])
async def CancelMatch(ctx):
    #コマンドを送信したユーザーを取得します。
    user = ctx.author
    if len(queue) < 1:
        # ゲームの待機キューが空の場合、ユーザーに通知します。
        await ctx.send('対局待ちしているプレイヤーがいません')
        await ctx.send('No players waiting for game')
    else:
        # キュー内にゲームが存在する場合、キャンセルするゲームをユーザーに選択させます
        await ctx.send('キャンセルする対局待ちを選択して下さい。選択はNo.の番号のみを入力してください\n' \
                       '例：3')
        await ctx.send('Please select the waiting game to cancel. Please enter only the number of the No.\n e.g. 3')
        await show_queue(ctx.message.channel) 
        def check_message(message):
            # メッセージが正しいユーザーからのもので、正しいチャンネルに投稿されたものであることを確認するための関数を定義します。
            return message.author == ctx.author and message.channel == ctx.channel
        try:
            message = await bot.wait_for('message', check=check_message, timeout=30)
            try:
                ### select_row:プレイヤーが選択した行番号
                select_row = int(message.content) 
                select_row = select_row - 1
                if select_row >= 0 and select_row < len(queue):
                    gameInfo = queue[select_row]
                    player1 = gameInfo.user
                    game_time = gameInfo.time
                    ### 同名プレイヤーの対局待ちのみキャンセルできるようにエラーチェック
                    if player1 == user:
                        await ctx.send(f'{user.mention} {player1}の{game_time}対局待ちをキャンセルしました。\n')
                        await ctx.send(f'{user.mention} {player1}  {game_time} waiting game has been cancelled. \n')
                        gameInfo = queue.pop(select_row)
                    else:
                        await ctx.send('あなたの対局待ちではない為キャンセルできません。')
                        await ctx.send('Cannot cancel because the game is not waiting for you.')
                else:
                    await ctx.send('無効な番号が入力されました。\n' \
                                   'マッチ選択コマンドからやり直してください')
                    await ctx.send('Invalid number entered. \n' \
                                   'Please start over with the match selection command')
            except ValueError:
                await ctx.send('番号を入力してください。\n' \
                               'マッチ選択コマンドからやり直してください')
                await ctx.send('Please enter a number. \n'\
                               'Please start over with the match selection command')
        except asyncio.TimeoutError:
            await ctx.send(f'{user.mention} タイムアウトしました。' \
                            '\nマッチ選択コマンドからやり直してください')
            await ctx.send(f'{user.mention} timed out.' \
                            'Please start over from the \n match selection command')

# "予約状況"あるいは"ReservationStatus"コマンドで現在の予約状況を連絡します。
@bot.command(aliases=['予約状況'])
async def ReservationStatus(ctx):
    await show_match_list(ctx.channel)

# 一定時間ごとにキューの中身に古い日付がある場合削除します。また、キュー内容を定期的に連絡します。
async def periodic_queue_update():
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    def game_refresh():
        # 現在の時間を取得し、時間が過ぎたゲームをキャンセルします。
        now = datetime.datetime.now()
        cancel_game = []
        if len(queue) == 0:
            return False,cancel_game
        else:
            result = False
            for i,q in enumerate(queue):
                if  q.date < now:
                    cancel_game.append(q)
                    queue.remove(q)
                    result = True
            return result,cancel_game
    while not bot.is_closed():
        # ボットが稼働している限り、期限切れのゲームをキャンセルし、キューの更新を続けます。
        result, cancel_game = game_refresh()   
        embed = discord.Embed(title="時間が過ぎたマッチの確認をしています……", color=0x00ff00)
        embed = discord.Embed(title="Checking for overdue matches ......", color=0x00ff00)
        if result:
            embed.add_field(name='', value=f'時間が過ぎたため以下の待ちがキャンセルされました', inline=False)
            embed.add_field(name='', value=f'The following wait has been canceled because time has passed', inline=False)
            embed.add_field(name='', value=f'No.', inline=True)
            embed.add_field(name='', value=f'User.', inline=True)
            embed.add_field(name='', value=f'Date.', inline=True)
            embed.add_field(name='', value=f'', inline=False)
            for i, q in enumerate(cancel_game):
                embed.add_field(name='', value=f'{i + 1}.', inline=True)
                embed.add_field(name='', value=f'{q.user}', inline=True)
                embed.add_field(name='', value=f'{q.time}', inline=True)
        else:
            embed.add_field(name='', value=f'キャンセルはありませんでした', inline=False)
            embed.add_field(name='', value=f'There were no cancellations', inline=False)
        await channel.send(embed=embed)
        await show_queue(channel)
        await asyncio.sleep(60 * 60 * 24)  # 24時間ごとに更新

# 「!マッチ選択」と入力されたら、対局待ちリストから選択してマッチングする処理
@bot.command(aliases=['マッチ選択'])
async def ChooseMatch(ctx):
    user = ctx.author
    if len(queue) < 1:
        # 対局待ちのキューが空の場合、ユーザーに通知します。
        await ctx.send('対局待ちしているプレイヤーがいません')
        await ctx.send('No players waiting for game')
    else:
        # キュー内に対局待ちが存在する場合、対局を選択するようユーザーに選択させます。
        await ctx.send('対局待ちのプレイヤーを選択して下さい。選択はNo.の番号のみを入力してください\n' \
                       '例：3')
        await ctx.send('Please select a player waiting for a game. Please enter only the number of the No.ߡn' \
                       'e.g. 3')
        await show_queue(ctx.message.channel) 
        def check_message(message):
            return message.author == ctx.author and message.channel == ctx.channel
        try:
            message = await bot.wait_for('message', check=check_message, timeout=30)
            try:
                select_row = int(message.content) 
                select_row = select_row - 1
                if select_row >= 0 and select_row < len(queue):
                    gameInfo = queue.pop(select_row)
                    player1 = gameInfo.user
                    game_time = gameInfo.time
                    await ctx.send(f'{user.mention} と {player1.mention} の対局が決定しました。\n' \
                                   f'スレッドでの調整を推奨します。対局日時： {game_time}')
                    await ctx.send(f'The game between {user.mention} and {player1.mention} has been decided. \n' )
                    await ctx.send('It is recommended to adjust the game in the 'f' thread. Game date and time: {game_time}')
                    match_list.append({'player1':player1,'player2':user,'date':game_time})
                else:
                    await ctx.send('無効な番号が入力されました。\n' \
                                   'マッチ選択コマンドからやり直してください')
                    await ctx.send('Invalid number entered. \n' \
                                   'Please start over with the match selection command')
            except ValueError:
                await ctx.send('番号を入力してください。\n' \
                               'マッチ選択コマンドからやり直してください')
                await ctx.send('Please enter a number. \n'\
                               'Please start over with the match selection command')
        except asyncio.TimeoutError:
            await ctx.send(f'{user.mention} タイムアウトしました。' \
                            '\nマッチ選択コマンドからやり直してください')
            await ctx.send(f'{user.mention} timed out.' \
                            'Please start over from the \n match selection command')


if __name__ == '__main__':
    bot.run(TOKEN)
