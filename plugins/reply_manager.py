# coding: utf-8

import pathlib
curpath = pathlib.Path(__file__)
import sys
sys.path.append(str(curpath.resolve().parent)) #カレントディレクトリの読み込み
from slackbot.bot import respond_to     # @botname: で反応するデコーダ
from slackbot.bot import listen_to      # チャネル内発言で反応するデコーダ
from slackbot.bot import default_reply  # 該当する応答がない場合に反応するデコーダ
import datetime
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
from dateutil.relativedelta import relativedelta
import random  #乱数発生
import re #正規表現を用いて文字列中を検索
from slacker import Slacker  #slack用の諸機能、特定チャンネル向けのメッセージが書ける
import slackbot_settings
slack = Slacker(slackbot_settings.API_TOKEN)
from my_modules import drive_manager as drv #drive_manager.pyで作った奴
from my_modules import calendar_manager as clnd  #calendar_manager.pyで作った奴
#from my_modules.mail_receiver import mail_get #メーリス廃止
from my_modules.weather import weather

# @respond_to('string')     bot宛のメッセージ
#                           stringは正規表現が可能 「r'string'」
# @listen_to('string')      チャンネル内のbot宛以外の投稿
#                           @botname: では反応しないことに注意
#                           他の人へのメンションでは反応する
#                           正規表現可能
# @default_reply()          DEFAULT_REPLY と同じ働き
#                           正規表現を指定すると、他のデコーダにヒットせず、
#                           正規表現にマッチするときに反応
#                           ・・・なのだが、正規表現を指定するとエラーになる？

# message.reply('string')   @発言者名: string でメッセージを送信
# message.send('string')    string を送信
# message.react('icon_emoji')  発言者のメッセージにリアクション(スタンプ)する
#                               文字列中に':'はいらない

yobi = ["月","火","水","木","金","土","日"]

def year_adder(dies_illa: 'datetime.date') -> 'datetime.date':
  #日附が今日より後なら今年の、前なら来年のyearを追加
  d_today = datetime.date.today()
  while dies_illa < d_today:
    dies_illa += relativedelta(years=1)
  return dies_illa


def reply_manager():#リプライで動く部分
  @respond_to('占')
  def uranai_func(message):
    tmp = random.randrange(10)
    if tmp < 1:
      message.reply('君の運勢は *大吉* だ!\nやったね!!')
    elif tmp < 3:
      message.reply('君の運勢は *吉* だ!\n喜ぶといいよ!')
    elif tmp < 5:
      message.reply('君の運勢は *中吉* だ!\n君にしてはついてる方だよ!')
    elif tmp < 7:
      message.reply('君の運勢は *小吉* だ!\n悲観することはないよ!')
    elif tmp < 9:
      message.reply('君の運勢は *凶* だ!\n悲観するがいいよ!')
    else:
      message.reply('君の運勢は *大凶* だ!\n苦しんで死ぬよ!！')


  @respond_to(r'極座標.*ラプラシアン.*')
  def laplacian_func(message):
    message.reply('3次元の極座標ラプラシアンは\n∆ ≡ (1/𝑟²)(∂/∂𝑟)(𝑟²∂/∂𝑟) + (1/𝑟²sin𝜃)(∂/∂𝜃)(sin𝜃∂/∂𝜃) + (1/𝑟²sin²𝜃)(∂²/∂𝜑²)\nだよ!憶えてね!')

  @respond_to(r'円筒座標.*ラプラシアン.*')
  def laplac2_func(message):
    message.reply('3次元の円筒座標ラプラシアンは\n∆ ≡ (1/𝑟)(∂/∂𝑟)(𝑟∂/∂𝑟) + (1/𝑟²)(∂²/∂𝜃²) + ∂²/∂𝑧²\nだよ!憶えてね!')

  @respond_to(r'人に勝てる.+だろ+.*')
  def bakayaro_func(message):
    message.reply('馬鹿野郎お前俺は勝つぞお前！！')

  @listen_to('あ、お前さ')
  def mur_func(message):
    message.send('そうだよ（便乗）')

  @listen_to(r'んにゃぴ.+なかった')
  def police_func(message):
    message.reply('んにゃぴ警察だ！')

  @respond_to(r'(?:(?:(?:[469]|(?:11))月(?:30|(?:[12]\d)|[1-9])日)|(?:(?:(?:10)|(?:12)|[13578])月(?:(?:3[01])|(?:[12]\d)|[1-9])日)|(?:2月(?:(?:[12]\d)|[1-9])日))') #'m月n日'という文言に反応
  def daily(message):
    text = message.body['text'] #投稿されたメッセージの取得
    dies = re.findall(r'(?:(?:(?:[469]|(?:11))月(?:30|(?:[12]\d)|[1-9])日)|(?:(?:(?:10)|(?:12)|[13578])月(?:(?:3[01])|(?:[12]\d)|[1-9])日)|(?:2月(?:(?:[12]\d)|[1-9])日))', text) #メッセージ内の日附の部分を見つける
    dies_illa = datetime.datetime.strptime(f'{datetime.date.today().year}/{dies[0]}', '%Y/%m月%d日').date()
    dies_illa = year_adder(dies_illa) #年を取得、附加
    yotei = clnd.calendar_get(dies_illa) #Googleカレンダー上の予定
    yotei += drv.get_sched(dies_illa) #スプレッドシートに登録された予定
    message.send(f'{dies_illa.month}月{dies_illa.day}日({yobi[dies_illa.weekday()]})の予定をお報せするよ！\n'
      + (yotei if yotei else 'この日の予定は無いよ！'))

  @respond_to(r'(?:(?:(?:[469]|(?:11))/(?:30|(?:[12]\d)|[1-9]))|(?:(?:(?:10)|(?:12)|[13578])/(?:(?:3[01])|(?:[12]\d)|[1-9]))|(?:2/(?:(?:[12]\d)|[1-9])))') #'m/n'という文言に反応
  def daily(message):
    text = message.body['text']
    dies = re.findall(r'(?:(?:(?:[469]|(?:11))/(?:30|(?:[12]\d)|[1-9]))|(?:(?:(?:10)|(?:12)|[13578])/(?:(?:3[01])|(?:[12]\d)|[1-9]))|(?:2/(?:(?:[12]\d)|[1-9])))', text) #メッセージ内の日附の部分を見つける
    dies_illa = datetime.datetime.strptime(f'{datetime.date.today().year}/{dies[0]}', '%Y/%m/%d').date()
    dies_illa = year_adder(dies_illa)
    yotei = clnd.calendar_get(dies_illa)
    yotei += drv.get_sched(dies_illa)
    message.send(f'{dies_illa.month}月{dies_illa.day}日({yobi[dies_illa.weekday()]})の予定をお報せするよ！\n'
      + (yotei if yotei else 'この日の予定は無いよ！'))

  @respond_to('今日')
  def tomorrow(message):
    d_today = datetime.datetime.now(JST).date()
    yotei = clnd.calendar_get(d_today)
    yotei += drv.get_sched(d_today)
    message.send(f'今日の予定をお報せするよ！\n天気は{weather(0)}だよ！\n'
      + (yotei if yotei else '今日の予定は無いよ！'))

  @respond_to('明日')
  def tomorrow(message):
    d_tom = datetime.datetime.now(JST).date() + datetime.timedelta(days=1)
    yotei = clnd.calendar_get(d_tom)
    yotei += drv.get_sched(d_tom)
    message.send(f'明日の予定をお報せするよ！\n天気は{weather(1)}だよ！\n'
      + (yotei if yotei else '明日の予定は無いよ！'))

  @respond_to('明後日')
  def perendinus(message):
    d_tom = datetime.datetime.now(JST).date() + datetime.timedelta(days=2)
    yotei = clnd.calendar_get(d_tom)
    yotei += drv.get_sched(d_tom)
    try:
      themessage = f'明後日の予定をお報せするよ！\n天気は{weather(2)}だよ！'
    except IndexError:
      themessage = '明後日の予定をお報せするよ！\n'
    themessage += yotei if yotei else '明後日の予定は無いよ！'
    message.send(themessage)

  @respond_to(r'(?:来週|一週間)')
  def septimana(message):
    yotei_calendar = clnd.week_get()
    yotei_drive = drv.get_week()
    yotei = [x+y for (x,y) in zip(yotei_calendar, yotei_drive)]
#    yotei = yotei_calendar
    if not any(yotei):
      message.send('一週間の予定は無いよ！\nクソ暇人だね！！')
    else:
      message.send('一週間の予定をお報せするよ！')
      d_itr = datetime.datetime.now(JST).date()
      tom = datetime.timedelta(days=1)
      for i in range(7):
        d_itr += tom
        if yotei[i]:
          try:
            yotei[i] = f'*{d_itr.month}月{d_itr.day}日({yobi[d_itr.weekday()]})* 天気:{weather(i+1)}\n' + yotei[i]
          except IndexError:
            yotei[i] = f'*{d_itr.month}月{d_itr.day}日({yobi[d_itr.weekday()]})*\n' + yotei[i]
          message.send(yotei[i])


  """
  @respond_to('maildebug')#開発用
  def mail_debuger(message):
    t_now = datetime.datetime.now(JST)
    mails = mail_get(t_now - datetime.timedelta(hours=20), t_now)
    print(mails)

    if mails:
      slack.chat.post_message('midoritest',f'{len(mails)}件の新着メールがあるよ！',as_user=True)

      for mail in mails:
        gotmail_title = f" *{mail['Subject']}* \n"
        if 'From' in mail:#Fromは無い場合有り
          gotmail = f"From : {mail['From']}\n"
          gotmail += f"{mail['Date']}\n\n"
        else:
          gotmail = f"{mail['Date']}\n\n"
        gotmail += f"{mail['Sentence']}"
        ts_illius = slack.chat.post_message('midoritest',gotmail_title,as_user=True)
        slack.chat.post_message('midoritest',gotmail,as_user=True,thread_ts=ts_illius.body['ts'])

        for key in mail['Files']:
          tmptmp=slack.files.upload(channels='midoritest',file_=mail['Files'][key],filename=key,thread_ts=ts_illius.body['ts'])
          print(tmptmp)
          mail['Files'][key].close()
    else:
      message.send('ないです')
  """
