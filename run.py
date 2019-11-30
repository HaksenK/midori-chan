# coding: utf-8
import sys
sys.path.append('/usr/local/lib/python3.7/site-packages')
#slackbotモジュールが上手くimportされなかったので2,3行目の文を追加した

from slackbot.bot import Bot

def main():
    bot = Bot()
    bot.run()

if __name__ == "__main__":
    print('start slackbot')
    main()
