# coding: utf-8

import pathlib
curpath = pathlib.Path(__file__)
import sys,os
sys.path.append(str(curpath.resolve().parent)) #カレントディレクトリの読み込み
from time import sleep
import datetime
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
import schedule
from slacker import Slacker  #slack用の諸機能、特定チャンネル向けのメッセージが書ける
import slackbot_settings
slack = Slacker(slackbot_settings.API_TOKEN)
from my_modules import drive_manager as drv #drive_manager.pyで作った奴
from my_modules import calendar_manager as clnd  #calendar_manager.pyで作った奴
from my_modules.mail_receiver import mail_get #メーリス廃止に伴い停止
from my_modules.weather import weather

yobi = ["月","火","水","木","金","土","日"]

def time_manager():#時間で動く部分
  if slackbot_settings.API_TOKEN == os.environ['SLACKBOT_API_TOKEN1']:#技系ワークスペースのみ
    #サブコンに練習メニューの催促
    def asita():#明日通常練乃至補充練が有ればリマインド
      d_tom = datetime.datetime.now(JST).date() + datetime.timedelta(days=1)
      pracname = clnd.pracname_get(d_tom)
      if '練習日' in pracname:
        slack.chat.post_message('練習連絡',"`明日のメニューお願いします`",as_user=True) #第一引数蓋し要変更

      elif '補充練' in pracname:
        slack.chat.post_message('練習連絡',f"`明日の{pracname}のメニューお願いします`",as_user=True) #第一引数蓋し要変更

    def asatte():#明後日通常練乃至補充練が有ればリマインド
      d_tom = datetime.datetime.now(JST).date() + datetime.timedelta(days=2)
      pracname = clnd.pracname_get(d_tom)
      if '練習日' in pracname:
        slack.chat.post_message('練習連絡',"`明後日の練習メニューを教えてください`",as_user=True)#第一引数蓋し要変更

      elif '補充練' in pracname:
        slack.chat.post_message('練習連絡',f"`明後日の{pracname}の練習メニューを教えてください`",as_user=True)#第一引数蓋し要変更

    #Herokuはアメリカかヨーロッパでしか登録できないのでグリニッジ時間で登録すること。つまり指定した時間の九時間後となる。"05:00"を指定すれば14:00に起動する
    schedule.every().day.at("05:00").do(asatte)
    schedule.every().day.at("05:00").do(asita)


  if slackbot_settings.API_TOKEN == os.environ['SLACKBOT_API_TOKEN2']:#全体用ワークスペースのみ
    def daily2():
      d_tom = datetime.datetime.now(JST).date() + datetime.timedelta(days=1)
      yotei = clnd.calendar_get(d_tom)
      yotei += drv.get_sched(d_tom)
      if yotei:
        try:
          slack.chat.post_message('04_予定',f'明日の予定をお報せするよ！\n天気は{weather(1)}だよ！\n' + yotei,as_user=True)
        except IndexError:
          slack.chat.post_message('04_予定','明日の予定をお報せするよ！\n' + yotei ,as_user=True)

      nokori_days = clnd.until_next_concert()
      if nokori_days >= 0 and (nokori_days <= 15 or nokori_days%10==0 or (nokori_days<=30 and nokori_days%5==0)):
        slack.chat.post_message('04_予定',f'次の演奏会迄あと{nokori_days}日だよ！',as_user=True)

    def weekly():
      yotei_calendar = clnd.week_get()
      yotei_drive = drv.get_week()
      yotei = [x+y for (x,y) in zip(yotei_calendar, yotei_drive)]
#      yotei = yotei_calendar
      if not any(yotei):
        slack.chat.post_message('04_予定','次週の予定をお報せするよ！\n次週の予定は無いよ！\nクソ暇人だね！！',as_user=True)
      else:
        slack.chat.post_message('04_予定','次週の予定をお報せするよ！',as_user=True)
        d_itr = datetime.datetime.now(JST).date()
        tom = datetime.timedelta(days=1)
        for i in range(7):
          d_itr += tom
          if yotei[i]:
            try:
              yotei[i] = f'*{d_itr.month}月{d_itr.day}日({yobi[d_itr.weekday()]})* 天気:{weather(i+1)}\n' + yotei[i]
            except IndexError:
              yotei[i] = f'*{d_itr.month}月{d_itr.day}日({yobi[d_itr.weekday()]})*\n' + yotei[i]
            slack.chat.post_message('04_予定',yotei[i],as_user=True)


    def mail_reminder():
      t_now = datetime.datetime.now(JST)
      mails = mail_get(t_now - datetime.timedelta(minutes=1) - datetime.timedelta(seconds=10), t_now) #一分毎に一分十秒前から今迄のメールを取得(未読のみ)

      if mails:
#        slack.chat.post_message('11_メーリス',f'{len(mails)}件の新着メールがあるよ！',as_user=True)
        for mail in mails:
          gotmail_title = f" *{mail['Subject']}* \n"
          if 'From' in mail:#Fromは無い場合有り
            gotmail = f"From : {mail['From']}\n"
            gotmail += f"{mail['Date']}\n\n"
          else:
            gotmail = f"{mail['Date']}\n\n"
          gotmail += f"{mail['Sentence']}"
          ts_illius = slack.chat.post_message('11_メーリス',gotmail_title,as_user=True)#此件名の投稿にスレッドとして内容を投稿する為にthread_tsを取得する
          slack.chat.post_message('11_メーリス',gotmail,as_user=True,thread_ts=ts_illius.body['ts'])#本文をスレッドとして投稿

          for key in mail['Files']:
            slack.files.upload(channels='11_メーリス',file_=mail['Files'][key],filename=key,thread_ts=ts_illius.body['ts'])#Slackにファイルをアップロード
            mail['Files'][key].close()#BytesIOオブジェクトは使い終わったらちゃんと閉じようね

    #Herokuはアメリカかヨーロッパでしか登録できないのでグリニッジ時間で登録すること。つまり指定した時間の九時間後となる。"05:00"を指定すれば14:00に起動する
    schedule.every().day.at("07:30").do(daily2)
    schedule.every().sunday.at("07:30").do(weekly)
    schedule.every().minutes.do(mail_reminder)


  while True:#指定した時間が来る度に実行
    schedule.run_pending()
    sleep(1)
