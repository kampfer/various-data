import requests
import pandas as pd
import numpy as np

r = requests.get('http://127.0.0.1:3000/api/getIndicator?id=3b065983-7795-40dc-b104-48c072803d33')
data = r.json()
df = pd.DataFrame(data['data'])
df[['date']] = df[['date']].apply(pd.to_datetime, unit='ms')
df[['open', 'close', 'top', 'bottom']] = df[['open', 'close', 'top', 'bottom']].apply(pd.to_numeric)
df.set_index('date', inplace=True)
yearly = df.resample('BA')
print(yearly.count())