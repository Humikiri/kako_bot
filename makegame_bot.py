import discord
from discord.ext import commands
import asyncio
from collections import deque
import datetime

intents=discord.Intents.all()
# Botのトークン
TOKEN = 'MTEwNTQ0Mzk1NDkxMDA0NDI3MA.GrEqM5.k8ugIKGAGjU_Er9EEdZ5NSOb8GxW8vJt6DJKh4'

# Botのコマンドプレフィックス
bot = commands.Bot(command_prefix='!', intents=intents)

# 対局待ちリストを管理するリスト
queue = []
#マッチング成立済みリストを管理する
match_list = []

@bot.command()
async def ヘルプ(ctx):
    embed = discord.Embed(title="ヘルプ", description="使い方", color=0x00ff00)
    embed.add_field(name="!対局したい", value="対局待ちリストに追加するコマンドです。Botが日付入力を求めます。", inline=False)
    embed.add_field(name="!対局待ち", value="現在の対局待ちリストを表示します。", inline=False)
    embed.add_field(name="!マッチ選択", value="対局待ちリストから参加するマッチを選びます。", inline=False)
    embed.add_field(name="!キャンセル", value="対局待ちリストから自分自身を削除するコマンドです。", inline=False)
    embed.add_field(name="!予約", value="現在の対局予約リストを表示します。", inline=False)
    await ctx.send(embed=embed)

# 対局待ちリストに新しいプレイヤーを追加する関数
def add_to_queue(user, date):
    if len(queue) == 0:
        queue.append({'user': user, 'date': date})
        return True
    else:
        if user not in [q['user'] for q in queue]:
            queue.append({'user': user, 'date': date})
            return True
        else:
            return False

# 対局待ちリストからプレイヤーを削除する関数
def remove_from_queue(user):
    if len(queue) == 0:
        return False
    else:
        result = False
        for i,q in enumerate(queue):
            if user == q['user']:
                queue.remove(q)
                result = True
        return result

# 対局待ちリストの状況を表示する関数
async def show_queue(channel):
    if len(queue) == 0:
        await channel.send('誰も対局待ちしていません。')
    else:
        queue_list = '\n'.join([f'{i+1}. | {q["user"]} | {q["date"]}' for i,q in enumerate(queue)])
        bar = '-----------------------------\n'
        await channel.send(bar + f'現在の対局待ちリスト\nNO. | user | date \n{queue_list}\n' + bar)

# BOT起動時に実行される処理
@bot.event
async def on_ready():
    print('ログインしました')
    bot.loop.create_task(periodic_queue_update())

# 「!対局したい」と入力されたら、対局待ちリストにユーザを追加する処理
@bot.command()
async def 対局したい(ctx):
    user = ctx.author
    await ctx.send(f'{user.mention} 希望の日時を入力してください（形式：年-月-日 時:分）')
    def check_message(message):
        return message.author == ctx.author and message.channel == ctx.channel
    try:
        message = await bot.wait_for('message', check=check_message, timeout=30)
        datetime_str = message.content
        try:
            game_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            if game_time > datetime.datetime.now():
                if add_to_queue(user, game_time):
                    await ctx.send(f'{user.mention}が対局待ちになりました。日時： {game_time} ')
                else:
                    await ctx.send(f'{user.mention}はすでに対局待ち中です。')
            else:
                await ctx.send(f'{user.mention} 入力された日時は {game_time} です')
                await ctx.send( '過去の日付になっています。\n' \
                                '対局希望コマンドからやり直してください')
        except ValueError:
            await ctx.send('日時の形式が正しくありません。YYYY-MM-DD HH:MM形式で入力してください。\n' \
                           '対局希望コマンドからやり直してください')
    except asyncio.TimeoutError:
        await ctx.send(f'{user.mention} タイムアウトしました。' \
                        '\n対局希望コマンドからやり直してください')

# 「!対局待ち」と入力されたら、対局待ちリストの状況を表示する処理
@bot.command()
async def 対局待ち(ctx):
    user = ctx.author
    await show_queue(ctx.message.channel) 

# 「!キャンセル」と入力されたら、対局待ちリストからユーザを削除する処理
@bot.command()
async def キャンセル(ctx):
    user = ctx.author
    if remove_from_queue(user):
        await ctx.send(f'{user.mention}が対局待ちリストから削除されました。')
    else:
        await ctx.send(f'{user.mention}は対局待ちリストに登録されていません。')

# 日付が過ぎていたら対局待ちリストから削除する機能
def game_refresh():
    now = datetime.datetime.now()
    cancel_game = []
    if len(queue) == 0:
        return False,cancel_game
    else:
        result = False
        for i,q in enumerate(queue):
            if  q['date'] < now:
                cancel_game.append(q)
                queue.remove(q)
                result = True
        return result,cancel_game
    
# 1時間おきに対局待ちリストの状況を表示する処理
async def periodic_queue_update():
    await bot.wait_until_ready()
    channel = bot.get_channel(1105972238747963522) # チャンネルIDを指定してください
    while not bot.is_closed():
        result, cancel_game = game_refresh()    
        if result:
            cancel_str = '\n'.join([f'{i+1}. | {q["user"].mention} | {q["date"]}' for i,q in enumerate(cancel_game)])
            await channel.send(f'時間が過ぎたため以下の待ちがキャンセルされました\nNO. | user | date \n{cancel_str}')
        await show_queue(channel)
        await asyncio.sleep(3600) #1時間待機

# 「!マッチ選択」と入力されたら、対局待ちリストから選択してマッチングする処理
@bot.command()
async def マッチ選択(ctx):
    user = ctx.author
    if len(queue) < 1:
        await ctx.send('対局待ちしているプレイヤーがいません')
    else:
        await ctx.send('対局待ちのプレイヤーを選択して下さい。選択はNo.の番号のみを入力してください\n' \
                       '例：3')
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
                    player1 = gameInfo['user']
                    player2 = user
                    gamedate = gameInfo['date']
                    await ctx.send(f'{player1.mention} vs {player2.mention} の対局が成立しました！' \
                                    '日時：' + gamedate.strftime('%Y/%m/%d %H:%M') + '\n' \
                                    '個別に対局の調整をして下さい。（スレッドの作成を推奨）')
                    match_list.append({'player1':player1, 'player2':player2, 'date':gamedate})
                else:
                    print(select_row)
                    await ctx.send("選択が正しくありません。"\
                                "\n選択コマンドからやり直してください")        
            except Exception as e:
                print('message.content' + message.content) 
                print(e)
                await ctx.send("入力が正しくありません。"\
                            "\n選択コマンドからやり直してください")
        except asyncio.TimeoutError:
            await ctx.send(f'{user.mention} タイムアウトしました。' \
                            '\n対局希望コマンドからやり直してください')

# 「!予約」と入力されたら、対局マッチング済みのリストを表示する処理
@bot.command()
async def 予約(ctx):
    # 日付が過ぎていたらマッチングリストから削除
    def del_matching():
        now = datetime.datetime.now()
        if len(match_list) == 0:
            return False
        else:
            result = False
            for i,q in enumerate(match_list):
                if  q['date'] < now:
                    match_list.remove(q)
                    result = True
            return result
    # 対局待ちリストの状況を表示する関数
    async def show_match(channel):
        if len(match_list) == 0:
            await channel.send('マッチング済みリストがありません')
        else:
            mat_list = '\n'.join([f'{i+1}. | {q["player1"]}| {q["player2"]} | {q["date"]}' for i,q in enumerate(match_list)])
            await channel.send(f'現在のマッチング済みリスト\nNO. | player1 | player2 | date \n{mat_list}')
    del_matching()
    await show_match(ctx.message.channel)

bot.run(TOKEN)