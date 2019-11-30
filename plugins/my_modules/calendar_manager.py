######################Google Calendar######################
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import apiclient
import os, pathlib
curpath = pathlib.Path(__file__)

scopes = ['https://www.googleapis.com/auth/calendar.readonly']
json_file = curpath.resolve().parent / 'slack_project.json'#OAuth用クライアントIDの作成でダウンロードしたjsonファイル、認証情報のサービス アカウント キーからダウンロードできる
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scopes=scopes)
http_auth = credentials.authorize(Http())

# カレンダー用クライアントの準備
service = apiclient.discovery.build("calendar", "v3", http=http_auth)#API利用できる状態を作る
######################Google Calendar_end##################
import datetime
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
from typing import Dict, List

class CalendarManager:
  def __init__(self, the_day: 'datetime.date'):
    #先ず初めと終わりの日附を指定
    self.__the_day = the_day

  def __calend_get(self, day_itr=datetime.timedelta(days=0)) -> Dict[str,str]:
    calendar_id = os.environ['PRACTICE_ID']#カレンダーIDの指定、カレンダー1の取得
    dtfrom = (self.__the_day + day_itr).isoformat() + "T00:00:00.000000Z"
    dtto = (self.__the_day + day_itr).isoformat() + "T15:00:00.000000Z" #二十四時間で取得すると次の日の予定も取れて了う。我が団のイベントカレンダーには時間指定が無いので十五時間で取得してもちゃんと一日分のイベントが取れる
    # API実行
    events_results = service.events().list(
            calendarId = calendar_id,
            timeMin = dtfrom,
            timeMax = dtto,
            maxResults = 50,
            singleEvents = True,
            orderBy = "startTime"
        ).execute()
    # API結果から値を取り出す
    events = events_results.get('items', [])
    return events

  def __events_get(self, day_itr: 'datetime.timedelta') -> Dict[str,str]:
    calendar_id = os.environ['EVENT_ID']#カレンダーIDの指定、カレンダー2の取得
    dtfrom = (self.__the_day + day_itr).isoformat() + "T00:00:00.000000Z"
    dtto = (self.__the_day + day_itr).isoformat() + "T15:00:00.000000Z" #二十四時間で取得すると次の日の予定も取れて了う。我が団のイベントカレンダーには時間指定が無いので十五時間で取得してもちゃんと一日分のイベントが取れる
    # API実行
    events_results = service.events().list(
            calendarId = calendar_id,
            timeMin = dtfrom,
            timeMax = dtto,
            maxResults = 50,
            singleEvents = True,
            orderBy = "startTime"
        ).execute()
    # API結果から値を取り出す
    events = events_results.get('items', [])
    return events

  def practice_trim(self, day_itr=datetime.timedelta(days=0)) -> str:
    #カレンダー1からの取得部分
    events = self.__calend_get(day_itr)
    yotei = ''
    if not events:
      return yotei
    for event in events:
      yotei += "```\n"
      yotei += f"イベント名 : {event['summary']}\n"
      if 'location' in event:
        yotei += f"場所 : {event['location']}\n"
      if 'start' in event:
        if 'dateTime' in event['start']:
          d_event = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S+09:00')
          yotei += f'開始時間 : {d_event.hour:02}:{d_event.minute:02}\n'
      if 'end' in event:
        if 'dateTime' in event['end']:
          d_event = datetime.datetime.strptime(event['end']['dateTime'], '%Y-%m-%dT%H:%M:%S+09:00')
          yotei += f'終了時間 : {d_event.hour:02}:{d_event.minute:02}\n'
      if 'description' in event:
        yotei += f"備考 : {event['description']}\n"
      yotei += "```\n"
    return yotei

  def event_trim(self,day_itr=datetime.timedelta(days=0)) -> str:
    #カレンダー2からの取得部分
    events = self.__events_get(day_itr)
    yotei = ''
    if not events:
      return yotei
    for event in events:
      yotei += "```\n"
      yotei += f"イベント名 : {event['summary']}\n"
      if 'location' in event:
        yotei += f"場所 : {event['location']}\n"
      if 'start' in event:
        if 'dateTime' in event['start']:
          d_event = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S+09:00')
          yotei += f'開始時間 : {d_event.hour:02}:{d_event.minute:02}\n'
        elif 'date' in event['start']:
          d_event = datetime.datetime.strptime(event['start']['date'], '%Y-%m-%d')
      if 'end' in event:
        if 'dateTime' in event['start']:
          d_event = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S+09:00')
          yotei += f'終了時間 : {d_event.hour:02}:{d_event.minute:02}\n'
        elif 'date' in event:
          d_event = datetime.datetime.strptime(event['end']['date'], '%Y-%m-%d')
      if 'description' in event:
        yotei += f"備考 : {event['description']}\n"
      yotei += "```\n"
    return yotei


  def ifpractice(self) -> str:
    events = self.__calend_get()
    yotei = ''
    for event in events:
      yotei += event['summary']
    return yotei


  def concert_search(self) -> int: #次のコンサート迄何日
    remained_days = 0
    while remained_days <= 100:
      remained_days += 1
      the_ev = self.__events_get(datetime.timedelta(days=remained_days))
      if not the_ev: continue
      if the_ev[0]['summary'].rfind('コンサート') >= 0 or the_ev[0]['summary'].rfind('演奏会') >= 0:
        return remained_days
    return -1


def calendar_get(the_day: 'datetime.date') -> str:
  cal = CalendarManager(the_day)
  yotei = cal.practice_trim()
  yotei += cal.event_trim()
  del cal
  return yotei

def week_get() -> List[str]:
  cal = CalendarManager(datetime.datetime.now(JST).date())
  yotei = [0] * 7
  for i in range(7):
    yotei[i] = cal.practice_trim(datetime.timedelta(days=i+1))
    yotei[i] += cal.event_trim(datetime.timedelta(days=i+1))
  del cal
  return yotei

def pracname_get(the_day: 'datetime.date') -> str:
  cal = CalendarManager(the_day)
  yotei = cal.ifpractice()
  del cal
  return yotei

def until_next_concert() -> int:
  cal = CalendarManager(datetime.date.today())
  nokori_days = cal.concert_search()
  del cal
  return nokori_days

if __name__ == '__main__':
  yotei = calendar_get(datetime.date(2019,5,2))
  print(yotei)
  yotei = pracname_get(datetime.date(2019,5,2))
  print(yotei)
  nokori_days = until_next_concert()
  print(f'{nokori_days} days')
