# parValue = 1000 # 面值
# statedRate = 0.05 # 票面利率
# effectiveRate = 0.04 # 市场利率
# terms = 10

# https://zhuanlan.zhihu.com/p/30451334?utm_source=wechat_session
def calcBondPrice(parValue, statedRate, effectiveRate, terms):
  discountOfInterest = 0;
  for i in range(terms):
    discountOfInterest += (parValue * statedRate) / (1 + effectiveRate) ** (i + 1)

  discountOfParValue = parValue / (1 + effectiveRate) ** terms

  return discountOfInterest + discountOfParValue

print(calcBondPrice(1000, 0.05, 0.04, 10))
