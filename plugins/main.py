import os, sys, pathlib
curpath = pathlib.Path(__file__)
sys.path.append(str(curpath.resolve().parent)) #何故かstrに変換しないと読み込んで呉れない
import threading #リプライで動く函数reply_manager()と時間で動く函数time_manager()とを並行処理させている
import slackbot_settings as ss
from reply_manager import reply_manager
from time_manager import time_manager
if ss.API_TOKEN == os.environ['SLACKBOT_API_TOKEN2']:
  from log_obtain import get_log

t1 = threading.Thread(target=reply_manager)
t2 = threading.Thread(target=time_manager)
if ss.API_TOKEN == os.environ['SLACKBOT_API_TOKEN2']:
  t3 = threading.Thread(target=get_log)

t1.start()
t2.start()
if ss.API_TOKEN == os.environ['SLACKBOT_API_TOKEN2']:
  t3.start()
