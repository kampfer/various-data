import akshare as ak
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

df = ak.index_zh_a_hist(symbol="000001")
prices = df["收盘"]

prominence = (prices.max() - prices.min()) * 0.2

peaks, _ = find_peaks(prices, prominence=prominence)
valleys, _ = find_peaks(-prices, prominence=prominence)
# peaks, _ = find_peaks(prices, distance=150, rel_height=0.2)
# valleys, _ = find_peaks(-prices, distance=150, rel_height=0.2)

# peaks, _ = find_peaks(prices[peaks])

plt.plot(prices)
plt.plot(peaks, prices[peaks], "x", color="r")
plt.plot(valleys, prices[valleys], "o", color="g")

plt.show()

# print(df.head())
