######################Google Drive#########################
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import gspread

scopes = ['https://www.googleapis.com/auth/spreadsheets']

import os
doc_id_schedule = os.environ['DOC_ID_SCHED']#これはスプレッドシートのURLのうちhttps://docs.google.com/  spreadsheets/d/以下の部分です
doc_id_log = os.environ['DOC_ID_LOG']
######################Google Drive_end#####################
import pathlib
curpath = pathlib.Path(__file__)
import datetime
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
import re
import json
import bisect
from typing import List, Dict, Tuple
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


class DriveManager(object):
  def __init__(self, doc_id: str):
    #https://qiita.com/analytics-hiro/items/cd16060f1a9124e75376
    #access_tokenの有効期限が頗る短いのでget_sched()函数を呼び出す度にtokenの発行をやり直させる
    #refresh_tokenとか云うのを取得すれば一々トークンの再発行をしなくても良いらしいが面倒い
    #一応それっぽい事が書いてあるサイト(https://qiita.com/iwaseasahi/items/2363dc1d246bc06baeae)もあったのでメモしておく

    self.__json_file = curpath.resolve().parent / 'slack_project.json'#OAuth用クライアントIDの作成でダウンロードしたjsonファイル、認証情報のサービス アカウント キーからダウンロードできる
    self.__credentials = ServiceAccountCredentials.from_json_keyfile_name(self.__json_file, scopes=scopes)
    http_auth = self.__credentials.authorize(Http())

    self.__client = gspread.authorize(self.__credentials)
    self._gfile = self.__client.open_by_key(doc_id)#読み書きするgoogle spreadsheet


class ScheduleGet(DriveManager):
  #明日の予定をスプレッドシートから取得
  def __init__(self, doc_id: str, the_day: 'datetime.date'):
    super().__init__(doc_id)
    self.__the_day = the_day

  def get_sched(self, day_itr=datetime.timedelta(days=0)) -> str:
    target_day = self.__the_day + day_itr
    yotei = ''
  #スプレッドシートからの取得部分
    dies_illa = target_day.strftime("%-m/%-d") #月と日とが一桁の時0埋めしない
    worksheet = self._gfile.worksheet(f"{target_day.month}月") #其の月のワークシートを指定
    sheet = worksheet.get_all_values() #其の月のワークシートを二次元配列として取得
    for i in range(len(sheet)): #これでsheetの列のサイズに制限できる
      if sheet[i][0] == dies_illa: #日附がマッチしたら表示
        yotei += "```\n"
        for j in range(i,len(sheet)):
          if sheet[j][1] != '': #二列目が空白でない限り詳細を表示する
            yotei += f'{sheet[j][1]} : {sheet[j][2]}\n'
          else:
            break
        yotei += "```\n"
    return yotei
# 返り値の例
# ```
# イベント名 : 最強雀士決定戦
# 場所 : 部室
# 開始時間 : 17:40
# 終了時間 : 20:15
# 備考 : テンリャンピン
# ```


def get_sched(the_day: 'datetime.date') -> str:
  the_schedule = ScheduleGet(doc_id_schedule, the_day)
  yotei = the_schedule.get_sched()
  del the_schedule
  return yotei

def get_week() -> List[str]:#一週間の予定を取得
  the_schedule = ScheduleGet(doc_id_schedule, datetime.datetime.now(JST).date())
  yotei = [0] * 7 #七日分の予定のリスト、取り敢えず中身0で確保だけ
  for i in range(7):
    yotei[i] = the_schedule.get_sched(datetime.timedelta(days=i+1))#日附を進め乍ら七日分の予定を取得
  del the_schedule
  return yotei



class FileFilledUpError(Exception):
  pass

class SlackLog(DriveManager):
  def __get_worksheet(self,channel: str) -> str:
    try:
      worksheet = self._gfile.worksheet(channel) #其の月のワークシートを指定
    except gspread.exceptions.WorksheetNotFound:
      #新しくワークシートを作ってタイムスタンプ欄を作成
      self._gfile.add_worksheet(title=channel, rows=50, cols=20)
      worksheet = self._gfile.worksheet(channel)
      for i in range(4,21,4):
        self.__text_cell_format(worksheet, i)
      worksheet.update_cell(1,1,'The latest timestamp->')
      worksheet.update_cell(1,2,0)
      self.__number_format(worksheet,channel,row=1,col=2)
      self.__number_format(worksheet,channel,col=1)

    return worksheet


  def __number_format(self, worksheet: 'Worksheet', channel: str, col: int, row:int=None):
    #Timestampの表示形式を小数点以下4桁表示
    sheetId = worksheet._properties['sheetId']
    body = {
      "requests": [
        {
          "repeatCell": {
            "range": {
              "sheetId": sheetId,
              "startRowIndex": 1,
              "startColumnIndex": col-1,
              "endColumnIndex": col
            },
            "cell": {
              "userEnteredFormat": {
                "numberFormat": {
                  "type": "NUMBER",
                  "pattern": "0.0000"
                }
              }
            },
            "fields": "userEnteredFormat.numberFormat"
          }
        }
      ]
    }
    if row != None:
      body['requests'][0]['repeatCell']['range']['startRowIndex'] = row-1
      body['requests'][0]['repeatCell']['range']['endRowIndex'] = row
      body['requests'][0]['repeatCell']['range']['startColumnIndex'] = col-1
      body['requests'][0]['repeatCell']['range']['endColumnIndex'] = col

    self._gfile.batch_update(body)


  def __text_cell_format(self, worksheet: 'Worksheet', col: int):
    #セルの幅と文字列折り返しの設定変更
    sheetId = worksheet._properties['sheetId']
    body = {
      "requests": [
        {
          "updateDimensionProperties": { #セルの幅変更
            "range": {
              "sheetId": sheetId,
              "dimension": "COLUMNS",
              "startIndex": col-1,
              "endIndex": col
            },
            "properties": {
              "pixelSize": 300
            },
            "fields": "pixelSize"
          }
        },
        {
          "updateCells": { #文字列がセルを食み出したら折り返すように
            "range": {
              "sheetId": sheetId,
              "startRowIndex": 1,
              "startColumnIndex": col-1,
              "endColumnIndex": col
            },
            "rows": [
              {
                "values": [
                  {
                    "userEnteredFormat": {
                      "wrapStrategy": "WRAP"
                    }
                  }
                ]
              }
            ],
            "fields": "userEnteredFormat.wrapStrategy"
          }
        }
      ]
    }
    self._gfile.batch_update(body)


  def __writing(self, worksheet: 'Worksheet', itr:int, how_many_cols:int, log:Dict[str,str], col_count: int, row_count: int, latest_ts: str) -> Tuple[int,int]:
    #Worksheetのサイズが足りなければ追加
    if how_many_cols+4 > col_count:
      col_count += 4
      try:
        worksheet.resize(cols=col_count) #worksheet.add_cols()はループ内で2回以上起動しないっぽい（巫山戯んな）
      except gspread.exceptions.APIError as err:
        errcode = json.loads(err.args[0])['error']['code']
        #エラーコードが429ならAPIの100秒100回の利用制限に引っ掛かっている丈け
        if errcode == 429:
          sleep(100)
          try:
            worksheet.resize(cols=col_count)
          except gspread.exceptions.APIError:
            raise FileFilledUpError
        #エラーコード400ならスプレッドシートの500万セル制限に引っ掛かった
        elif errcode == 400:
          self.__set_latest_ts(worksheet, latest_ts)
          raise FileFilledUpError

    #一投稿分を記録
    cell_list = worksheet.range(itr,how_many_cols+1,itr,how_many_cols+4)
    for (cell,key) in zip(cell_list,log): #
      if key == 'thread_ts':
        continue
      if how_many_cols > 0 and key == 'ts':
        continue
      elif key == 'ts':
        cell.value = float(log[key])
        continue
      cell.value = log[key]

    worksheet.update_cells(cell_list)
    return col_count, row_count


  def get_latest_ts(self, worksheet:'Worksheet'=None, channel:str=None) -> str:
    if worksheet:
      return worksheet.cell(1,2).value
    elif channel:
      return self.__get_worksheet(channel).cell(1,2).value

  def __set_latest_ts(self, worksheet: 'Worksheet', latest_ts: str):
    worksheet.update_cell(1,2,latest_ts)


  def log_write(self, channel: str, logs: List[str]):
    #リストの内容をスプレッドシートに書き出す
    worksheet = self.__get_worksheet(channel)
    latest_ts = self.get_latest_ts(worksheet) #最終投稿時間
    col_count = worksheet.col_count #現在のワークシートの列の数、何故かワークシートをadd_cols()で広げても変わらない（おかしいだろ）ので自前の変数にして手動で変更
    row_count = worksheet.row_count
    ts_list = worksheet.col_values(1)
    try:
      ts_list.pop(0)
    except IndexError:
      pass
    ts_list = list(map(float, ts_list))

    for log in logs:
      if re.fullmatch(r'@.+さんがチャンネルに参加しました',log['text']):
        continue
      elif not log['text']:
        log['text'] = "A file or NULL"
      #thread_tsが同じものが有れば同じスレッドなので同じ行に、然うでなければ最新行にログを追加
      thread_num = len(ts_list)

      if 'thread_ts' in log:
        is_the_same_thread = bisect.bisect_left(ts_list, float(log['thread_ts'])) #保存したいログのタイムスタンプを二分探索。一致するものが無ければ基本的に新しいログのタイムスタンプが最大になるはずなので、bisectの挙動上一番右端の値がreturnする。之を其儘ts_listのインデックスとすると食み出てIndexErrorとなるので下のifで1引いている
        if is_the_same_thread == thread_num:
          is_the_same_thread -= 1
        if not ts_list:
          itr = 2
        elif ts_list[is_the_same_thread] == float(log['thread_ts']):
          itr = is_the_same_thread + 2 #gspreadの表番号は1から始まるので+1, スプレッドシートの最初の行はThe latest timestampを入れているのでログの始まりは更に+1
        else:
          itr = thread_num + 2
      else:
        itr = thread_num + 2

      if itr <= row_count:
        how_many_cols = len(worksheet.row_values(itr))
      else:
        #必要ならセルを下に追加
        how_many_cols = 0
        row_count += 50
        try:
          worksheet.resize(rows=row_count)
        except gspread.exceptions.APIError as err:
          errcode = json.loads(err.args[0])['error']['code']
          #エラーコードが429ならAPIの100秒100回の利用制限に引っ掛かっている丈け
          if errcode == 429:
            sleep(100)
            try:
              worksheet.resize(rows=row_count)
            except gspread.exceptions.APIError:
              raise FileFilledUpError
          #エラーコード400ならスプレッドシートの500万セル制限に引っ掛かった
          elif errcode == 400:
            self.__set_latest_ts(worksheet, latest_ts)
            raise FileFilledUpError

      #其の行が空なら行の頭から埋める。空でないなら一つスペースを空けて2つ先から始め、タイムスタンプは記録しない。
      col_count, row_count = self.__writing(worksheet, itr, how_many_cols, log, col_count, row_count, latest_ts)
      if how_many_cols == 0:
        ts_list.append(float(log['ts']))

      #ログを一行記録したらタイムスタンプ更新
      latest_ts = log['ts']

    #forを抜けたら最新タイムスタンプを登録
    self.__set_latest_ts(worksheet, latest_ts)

  def get_sheetslist(self) -> List["gspread.models.Worksheet"]:
    return self._gfile.worksheets()

  def delete_sheet(self, sheetobj: "gspread.models.Worksheet"):
    self._gfile.del_worksheet(sheetobj)

  def reinit_sheet(self, sheetobj: "gspread.models.Worksheet"):
    recent_ts = sheetobj.cell(1,2).value
    sheetobj.clear()
    sheetobj.resize(50,20)
    sheetobj.update_cell(1,1,'The latest timestamp->')
    sheetobj.update_cell(1,2,recent_ts)


def log_write(channel:str, logs:List[Dict[str,str]]):
  logger.log(10, channel)
  logger.log(10, logs)
  slog = SlackLog(doc_id_log)
  slog.log_write(channel, logs)
  del slog
  logger.log(20, f'Got the log of {channel}')

def fetch_latest_ts(channel:str) -> str:
  slog = SlackLog(doc_id_log)
  ts = slog.get_latest_ts(channel=channel)
  del slog
  return ts

def reinit_spreadsheet(channels: List[str]):
  fc = FileCopy(doc_id_log)
  sheetobjs = fc.get_sheetslist()
  for obj in sheetobjs:
    if obj.title in channels:
      fc.reinit_sheet(obj)
    else:
      fc.delete_sheet(obj)
  del fc


class FileCopy:
  #12月頭にログファイルを新しく
  def __init__(self, doc_id: str):
    self.__json_file = curpath.resolve().parent / 'slack_project-22da2e82f606.json'
    self.__credentials = ServiceAccountCredentials.from_json_keyfile_name(self.__json_file, scopes="https://www.googleapis.com/auth/drive")
    http_auth = self.__credentials.authorize(Http())
    self.__service = build('drive', 'v3', http=http_auth)

  def get_filenames(self) -> List[Dict[str, str]]:
    filenames = self.__service.files().list(
      includeItemsFromAllDrives=True,
      supportsAllDrives=True,
      fields="nextPageToken, files(id, name, parents)",
      q="name contains 'Slack_log' \
        and mimeType='application/vnd.google-apps.spreadsheet'"
    ).execute() #deprecatedな引数が一杯あるので修正が必要かも
    return filenames['files'] # type: List[Dict['id', 'name', 'parents']]

  def copy_file(self, name: str,fileid: str, parentids: List[str]) -> Dict[str, str]:
    retval = self.__service.files().copy(
      fileId=fileid,
      body={
        'name': name,
        'parents': parentids,
      }
    ).execute()
    return retval

  def rename(self, newname: str, fileid: str) -> Dict[str, str]:
    retval = self.__service.files().update(
      fileId=fileid,
      body={'name': newname}
    ).execute()
    return retval


def get_latest_filename(files: List[Dict[str, str]]) -> Dict[str, str]:
  retval = files[0]
  for afile in files:
    retval = afile if retval['name'] < afile['name'] else retval
  return retval if retval['id'] == doc_id_log else False


def get_generation(filename: str) -> str:
  if gen := re.search(r'[0-9]+', filename):
    gen = gen.group()
  return gen

def rename_logfile() -> bool:
  fc = FileCopy(doc_id_log)
  files = fc.get_filenames()
  if not files:
    del fc
    return False
  latest_file = get_latest_filename(files)
  if not latest_file:
    del fc
    return False
  current = get_generation(latest_file['name'])
  newname = re.sub(current, str(int(current)+1), latest_file['name'])
  try:
    fc.rename(newname, latest_file['id'])
  except HttpError:
    del fc
    return False
  try:
    fc.copy_file(latest_file['name'], latest_file['id'], latest_file['parents'])
  except HttpError:
    del fc
    return False
  return True


if __name__ == '__main__':
  print(get_sched(datetime.date(2019,4,29)))
  print(get_week())

  fc = FileCopy(doc_id_log)
  print(fc.get_filenames())
  del fc

  slog = SlackLog(doc_id_log)
  print(slog.get_sheetslist())
  del slog
