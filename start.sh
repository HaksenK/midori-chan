#!/bin/sh
tokens=($SLACKBOT_API_TOKEN1 $SLACKBOT_API_TOKEN2)
#SLACKBOT_API_TOKENはHeroku上で登録した環境変数。1には技系用ワークスペース、2には全体用ワークスペースのAPIトークンが格納されている

for token in ${tokens[@]}
do
export BOT_API_TOKEN=$token
python3 -B run.py &
done
wait
