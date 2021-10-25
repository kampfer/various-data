import requests
import pandas as pd
import numpy as np

r = requests.get('http://127.0.0.1:3000/api/getIndicator?id=3b065983-7795-40dc-b104-48c072803d33')
data = r.json()
df = pd.DataFrame(data['data'])
df[['date']] = df[['date']].apply(pd.to_datetime, unit='ms')
df[['open', 'close', 'top', 'bottom']] = df[['open', 'close', 'top', 'bottom']].apply(pd.to_numeric)
df.set_index('date', inplace=True)
# print(df.head())
# print(df.info())
# print(df.open)
yearly = df.resample('BA')  # resample之前必须保证索引是datetime类型
print(yearly.last().index.freq)
# print(df['date'].dt.year)
# everyYear = df.groupby(df['date'].dt.year)
# print(everyYear.last().close)