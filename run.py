# coding: utf-8
import sys
sys.path.append('/usr/local/lib/python3.7/site-packages')
#slackbotモジュールが上手くimportされなかったので2,3行目の文を追加した
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
from slackbot.bot import Bot

def main():
  bot = Bot()
  bot.run()

if __name__ == "__main__":
  logger.setLevel(20)
  logger.info('Start Slackbot')
  logger.setLevel(30)
  main()
