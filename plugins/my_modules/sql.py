"""
此スクリプトは弊団の役職をHerokuのPostgreSQLから検索できるようにしようとして、初代Slack責HaksenKが途中で面倒臭くなって投げたものです。
誰か完成させてあげて下さい。
"""

import os
import psycopg2 as pc2 #SQLの内Herokuで無料で使えるPostgreSQLを扱うモジュール
from datetime import date
from typing import List, Tuple

class sql_manager:
  def __init__(self):
    self.__DATABASE_URL = os.environ['DATABASE_URL']
    self.__conn = pc2.connect(self.__DATABASE_URL, sslmode='require')
    self.__cur = self.__conn.cursor()
#    self.__cur = self.__conn.cursor(cursor_factory=DictCursor)

  def file_output(self):
    self.__cur.execute("COPY jobs TO './data.txt' DELIMITERS '\t';")

  def file_input(self):
#    print('誤操作を防ぐ為に現在のデータベースを出力するよ！\nファイル名は\'old_database.txt\'だよ！')
#    self.file_output(filename='old_database.txt')
    self.__cur.execute("COPY 役職 FROM ''./data.txt' DELIMITER ','")


  def __latest_year(self) -> int: #存在するテーブルの内年度が最新のものを見つける
    year = int(date.today().strftime('%Y'))
    year += 1
    self.__cur.execute(f"SELECT * \
      FROM information_schema.tables \
      WHERE table_name='j{year}'")
    tmp = self.__cur.fetchall()
    while not tmp: #存在する年度のテーブルが見つかる迄繰り返し
      year -= 1
      self.__cur.execute(f"SELECT * \
        FROM information_schema.tables \
        WHERE table_name='j{year}'")
      tmp = self.__cur.fetchall()
    return year


  def find_name(self, job: str, year: int =None) -> List[Tuple[str,int]]:
    #役職名(と年度)から担当者と其の期を検索
    if not year: #デフォルトで最新年度版を取得
      year = self.__latest_year()

    self.__cur.execute(f"SELECT formal FROM synonym WHERE alias LIKE '%{job}%'") #別名検索(例: 「指揮者」->「サブコンダクター」)
    tmp = self.__cur.fetchall()
    if tmp: #若し別名が有ったらjobを正式名称に易える
      job = tmp[0][0]
    self.__cur.execute(f"SELECT a.name,a.generation FROM j{year} a \
        LEFT OUTER JOIN jobs b \
        ON b.key{year} = a.key \
        WHERE b.job LIKE '%{job}%'")
    return self.__cur.fetchall()


  def find_her_job(self, name: str, year: int =None) -> List[Tuple[str]]:
    #名前(と年度)から役職名を取得
    if not year: #デフォルトで最新年度版を取得
      year = self.__latest_year()

    self.__cur.execute(f"SELECT a.job FROM jobs a \
      LEFT OUTER JOIN j{year} b \
      ON a.key{year} = b.key \
      WHERE b.name LIKE '%{name}%'")
    return self.__cur.fetchall()


  def __del__(self):
    self.__cur.close()
    self.__conn.close()


if __name__ == '__main__':
  sql = sql_manager()
  print(sql.find_name('団長'))
  print(sql.find_her_job('田中'))
  del sql
