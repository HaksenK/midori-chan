from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import base64, email
import datetime
import re
import os
import pathlib
curpath = pathlib.Path(__file__)
from io import BytesIO
from typing import List, Dict, Tuple, Union

class GmailAPI:
  def __init__(self):
    # If modifying these scopes, delete the file token.json.
    self.__SCOPES = 'https://www.googleapis.com/auth/gmail.modify'


  def __ConnectGmail(self) -> 'googleapiclient.discovery.Resource':
    store = file.Storage(curpath.resolve().parent / 'credentials-gmail.json')
    creds = store.get()
    if not creds or creds.invalid:
      flow = client.flow_from_clientsecrets(curpath.resolve().parent / 'client_secret.json', self.__SCOPES)#OAuth Clientからダウンロードしたやつ
      creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()))
    return service


  def __DayDecoder(self, dies_illa: str) -> str:
    yobi = {'Sun,':'(日)', 'Mon,':'(月)', 'Tue,':'(火)', 'Wed,':'(水)', 'Thu,':'(木)', 'Fri,':'(金)', 'Sat,':'(土)'}
    tsuki = {'Jan':'1', 'Feb':'2', 'Mar':'3', 'Apr':'4', 'May':'5', 'Jun':'6', 'Jul':'7', 'Aug':'8', 'Sep':'9', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
    contents = dies_illa.split()
    return f'{contents[3]}年{tsuki[contents[2]]}月{contents[1]}日{yobi[contents[0]]} {contents[4][:5]}'


  def __GetSentence(self, service: 'googleapiclient.discovery.Resource', TheID: str) -> Tuple[str,Dict[str,'_io.BytesIO']] :#本文と添付ファイルとを詳らかに取得する
    #raw (1) rawフォーマットでメールを取得
    data = service.users().messages().get(userId='me', id=TheID, format='raw').execute()
    raw_data = base64.urlsafe_b64decode(data['raw'])
    # (2) Emailを解析する
    eml = email.message_from_bytes(raw_data)
    # (3) 本文を取得
    body = ""
    files = {} # type: Dict[str,'_io.BytesIO']

    for part in eml.walk(): # (4)テキスト部分の処理
      if part.get_content_type() == 'text/plain': # (5)
        s = part.get_payload(decode=True) # type: str
        if isinstance(s, bytes):
          charset = part.get_content_charset() or 'iso-2022-jp' # (6)
          s = s.decode(str(charset), errors="replace")
          s = re.sub(r"----------------------------------------------------------------------","@@@@@",s,flags=re.DOTALL).strip()
          s = re.sub(r"------------------------------------------------------\[freeml byGMO\]--","@@@[f]@@",s,flags=re.DOTALL).strip()
          s = re.sub(r"@@@@@([^@]|@[^@])+@@@\[f\]@@([^@]|@[^@])+@@@@@$","",s,flags=re.DOTALL).strip()#広告消し
          s = re.sub(r"@@@@@([^@]|@[^@])+@@@\[f\]@@\r\n\r\n","",s,flags=re.DOTALL).strip()#広告消し
          s = re.sub(r"@@@@@.+@@@@@","",s,flags=re.DOTALL).strip()#広告消し
          s = re.sub(r'<.+@.+>.+wrote:\r\n','wrote:\r\n',s,flags=re.DOTALL)#返信メールの場合元の送り主のメアドが見えるのでそれを消す
          s = re.sub(r' <.+@.+>:\r\n\r\n',':\r\n\r\n',s)#上と同じで返信メールの場合元の送り主のメアドを消す、書式が二種類あるっぽい
          daylists = re.findall(r'On \w{3}, \d+ \w{3,4} \d{4} \d{1,2}:\d{2}', s)#引用メールの日附の書式変更
          for daylist in daylists:
            tmpday = daylist
            tmpday = re.sub('On ', '', tmpday)
            s = re.sub(daylist, self.__DayDecoder(tmpday), s)
        body += s

      else:#添付ファイルの処理
        attach_fname = part.get_filename()#ファイル名
        if not attach_fname:
          continue
        decodefname = email.header.decode_header(attach_fname)#日本語のファイル名は'utf-8'でエンコードされているのでデコードする。返り値は[('ファイル名'、'エンコード形式')]と何故か要素一つ丈けのリストの中にタプルというよく分からん返り値になっているのでファイル名はdecodefname[0][0]で取り出す
        files[decodefname[0][0]] = BytesIO(part.get_payload(decode=True))#仮想的なファイル、"file-like object"に添付ファイルの詳細な中身（バイナリ？）を格納
    # (7) 本文を表示
    return body,files


  def GetMessageList(self,DateFrom: 'datetime.datetime',DateTo: 'datetime.datetime',MessageTo: str) -> Dict[str, Union[str,Dict[str,'_io.BytesIO']]]:

    #APIに接続
    service = self.__ConnectGmail()

    MessageList = [] # type: List[Dict[str, Union[str,Dict[str,'_io.BytesIO']]]]

    query = ''
    # 検索用クエリを指定する
    if DateFrom != None and DateFrom !="":
      query += 'after:' + str(int(DateFrom.timestamp())) + ' '#時間は整数Unix時間に変換
    if DateTo != None  and DateTo !="":
      query += 'before:' + str(int(DateTo.timestamp())) + ' '
    if MessageTo != None and MessageTo !="":
      query += 'To:' + MessageTo + ' '

    # メールIDの一覧を取得する(最大20件)
    messageIDlist = service.users().messages().list(userId='me',maxResults=20,q=query).execute()
    #該当するメールが存在しない場合は、処理中断
    if messageIDlist['resultSizeEstimate'] == 0:
      return MessageList

    #メッセージIDを元に、メールの詳細情報を取得
    for message in messageIDlist['messages']:
      row = {} # type: Dict[str, Union[str,Dict[str,'_io.BytesIO']]]
      row['ID'] = message['id']
      MessageDetail = service.users().messages().get(userId='me',id=message['id']).execute()
      if 'UNREAD' in MessageDetail['labelIds']:#未読を外す
        service.users().messages().modify(userId="me", id=message['id'], body={"removeLabelIds": ["UNREAD"]}).execute()
      else:#既読だったら無視する
        continue

      for header in MessageDetail['payload']['headers']:
        #日附、送信元、件名、本文、添付ファイルを取得する
        if header['name'] == 'Date':
          row['Date'] = self.__DayDecoder(header['value'])
        elif header['name'] == 'From':
          tmpfrom = header['value'][:re.search(r'\s*<',header['value']).start()]#[:re.search(r'\s*<',header['value']).start()]#で送り主メールアドレスとその直前の空白を除く
          if re.match('^".+"$',tmpfrom):#送り主名が""で囲まれていたら除く
            tmpfrom = re.sub('"','',tmpfrom)
          row['From'] = tmpfrom
          if(tmpfrom == '' or tmpfrom == r'\s+'):#送り主が空だったら辞書からFromを削除
            del row['From']
        elif header['name'] == 'Subject':
          row['Subject'] = header['value']
      row['Sentence'],row['Files'] = self.__GetSentence(service,row['ID'])
      MessageList.insert(0,row)
    return MessageList


def mail_get(fromtime: 'datetime.datetime', totime: 'datetime.datetime') -> Dict[str, Union[str,'_io.BytesIO']]:
  test = GmailAPI()
  messages = test.GetMessageList(DateFrom=fromtime,DateTo=totime,MessageTo=os.environ['MAILLIST_ADDRESS'])
  del test
  return messages


if __name__ == '__main__':
  fromtime = '2019-08-30T00:00:00'
  totime = '2019-08-31T12:00:00'
  date_dt1 = datetime.datetime.strptime(fromtime, '%Y-%m-%dT%H:%M:%S')
  date_dt2 = datetime.datetime.strptime(totime, '%Y-%m-%dT%H:%M:%S')
  messages = mail_get(date_dt1, date_dt2)
  #結果を出力
  if not messages:
    print('empty')
  for message in messages:
    print(message)
