import requests

def emoji_adder(wth: str) -> str:
  weathemoji = {'晴れ': '☀️', '曇り': '☁️', '雨': '☔️', '雪': '☃️', '晴時々曇': '⛅️', '晴のち曇': '🌥', '曇時々晴': '🌥', '曇のち晴': '🌤', '晴のち雨': '🌦️', '曇のち雨': '🌧️', '雨のち曇': '🌧️', '曇時々雨': '🌧️'}
  if wth in weathemoji:
    return wth + weathemoji[wth]
  else:
    return wth

def weather(i: int) -> str:
  url = 'http://weather.livedoor.com/forecast/webservice/json/v1'
  payload = {'city':'130010'} #東京
  tenki_data = requests.get(url, params=payload).json()
  return emoji_adder(tenki_data['forecasts'][i]['telop']) #i==0:今日、i==1:明日、i==2:明後日、以降はエラー

if __name__ == '__main__':
  for i in range(3):
    print(str(i)+":")
    try:
      print(weather(i))
    except IndexError:
      print("Error")
