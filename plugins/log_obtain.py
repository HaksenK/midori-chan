# coding: utf-8

import pathlib
curpath = pathlib.Path(__file__)
import sys,os
sys.path.append(str(curpath.resolve().parent)) #カレントディレクトリの読み込み
from slacker import Slacker  #slack用の諸機能、特定チャンネル向けのメッセージが書ける
import slackbot_settings
slack = Slacker(slackbot_settings.API_TOKEN)
import requests
import datetime
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
import re
from my_modules import drive_manager as drv
from time import sleep
import schedule
from typing import Dict
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def channel_get() -> Dict[str,str]:
  """
  Slackチーム内のチャンネルID、チャンネル名一覧を取得する。
  """

  # bodyで取得することで、[{チャンネル1},{チャンネル2},...,]の形式で取得できる。
  raw_data = slack.channels.list(exclude_archived=True).body

  result = []
  for data in raw_data["channels"]:
    result.append(dict(channel_id=data["id"], channel_name=data["name"]))

  return result


def get_message(channel: str, count: int=100):
  #最高1000件ずつしか取得できない
  params = urllib.urlencode(params)
  req = urllib2.Request("https://slack.com/api/channels.history")
  req.add_header('Content-Type', 'application/x-www-form-urlencoded')
  req.add_data(params)

  res = urllib2.urlopen(req)
  body = res.read()

  return body


def fetch_text(channel_id: str, oldest_message:float=0) -> Dict[str,str]:
#チャンネル内のメッセージを取得する
  SLACK_URL = "https://slack.com/api/channels.history"
  payload = {
    "channel": channel_id,
    "token": slackbot_settings.API_TOKEN,
    "oldest": oldest_message,
    "count": 1000
  }

  response = requests.get(SLACK_URL, params=payload)
  json_data = response.json()

  return json_data


def ts_to_time(unix: float) -> 'datetime.datetime':
  #UNIX時間から通常の時間表記への変換
  return datetime.datetime.fromtimestamp(int(float(unix)), JST)


def get_name(user_id: str) -> str:
  #User IDからUser nameを取得する
  payload = {'token': slackbot_settings.API_TOKEN, 'user': user_id}
  r = requests.get('https://slack.com/api/users.info', params=payload).json()
  if r['ok'] == False:
    return 'An unknown user'
  elif 'real_name' in r['user']:
    return r['user']['real_name']
  else:
    return r['user']['name']

def id_in_messages_translation(user_id: str) -> str:
  #<@User_ID>という形式を@User nameに変換
  user_id = user_id.lstrip('<@').rstrip('>')
  name = get_name(user_id)
  return '@' + name

def id_find(message: str) -> str:
  #<@User_ID>という形式をメッセージ中から探す。序でに変換
  id_list = re.findall(r'<@.+>',message)
  for id_ in id_list:
    message = message.replace(id_, id_in_messages_translation(id_))
  return message



def reform(messages: Dict[str,str]) -> Dict[str,str]:
  #チャンネル内メッセージデータの整形
  messages.reverse()
  reformed = []

  i = 0
  for message in messages:
    if 'user' in message:
      reformed.append( \
        { \
          'ts': message['ts'], \
          'time': ts_to_time(message['ts']).strftime('%Y-%m-%d %H:%M:%S'), \
          'name': get_name(message['user']), \
          'text': id_find(message['text']) \
        } \
      )

    else:
      reformed.append( \
        { \
          'ts': message['ts'], \
          'time': ts_to_time(message['ts']).strftime('%Y-%m-%d %H:%M:%S'), \
          'name': 'An Unknown User', \
          'text': id_find(message['text']) \
        } \
      )
    if 'thread_ts' in message:
      reformed[-1]['thread_ts'] = message['thread_ts']

  return reformed


renewing = False
def get_log_execution():
  if renewing: return #ログファイルの更新中は動かさない

  channels = channel_get()
  for channel in channels:
    oldest = float(drv.fetch_latest_ts(channel['channel_name'])) + 1 #最新timestampの次の投稿からget、本当はtimestampの0.0001秒後くらいから取得したいけどSlack APIに渡すと小数点以下の桁数が滅茶苦茶になるっぽい。恥ずかしくないのかよ?
    texts = fetch_text(channel['channel_id'], oldest)
    if not texts['messages']:
      continue
    t = reform(texts['messages'])
    try:
      drv.log_write(channel=channel['channel_name'], logs=t)
    except drv.FileFilledUpError:
      slack.chat.post_message('01_random','Error 400が返されたよ！ \
        ログを取っているスプレッドシートが一杯だよ！\
        新しいスプレッドシートを作ってHerokuの環境変数に登録してね！')
    else:
      sleep(100) #This version of the Google Sheets API has a limit of 500 requests per 100 seconds per project, and 100 requests per 100 seconds per user. Limits for reads and writes are tracked separately. There is no daily usage limit. https://developers.google.com/sheets/api/limits


def renew_logfile():
  #年に一度のログファイル更新
  renewing = True #作業中にログを取得しない
  sleep(100) #API制限に引っかかると面倒なので待つ
  retval = drv.rename_logfile()
  if not retval:
    logger.log(40, 'Renewing the log file failed.\nCouldn\'t find the log file.')
    renewing = False
    return
  channels = channel_get()
  channel_names = []
  for channel in channels:
    channel_names.append(channel['channel_name'])
  drv.reinit_spreadsheet(channel_names)
  logger.setLevel(20)
  logger.info('Slack log spreadsheet successfully reinitialised')
  logger.setLevel(30)
  renewing = False

def renew_logfile_execution():
  #元日に実行
  today = datetime.date.today()
  if today.month == 1 and today.day == 1:
    renew_logfile()


def get_log():
  schedule.every(2).hours.do(get_log_execution)
  schedule.every().day.at("00:00").do(renew_logfile_execution)
  """
  while True:
    schedule.run_pending()
    sleep(1)
  """
  #別スレッドでrun_pendingしているので此方ではやらない(二ヶ月悩んだ)



if __name__ == '__main__':
  channels = channel_get()
  for channel in channels:
    print(f'channel_id={channel}')
    oldest = float(drv.fetch_latest_ts(channel['channel_name'])) + 1
    texts = fetch_text(channel['channel_id'], oldest)
    t = reform(texts['messages'])
