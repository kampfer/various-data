from utils import crawlStatsData

def crawlYearlyPriceFixingIndex():
  crawlStatsData('hgnd', 'A0902', '1990-', 'yearly_price_fix_index')

# 全国居民消费价格分类指数（上年同月=100）（2016-）
def crawlMonthlyCPIYoY2016_():
  crawlStatsData('hgyd', 'A010101', '2016-', 'monthly_cpi_yoy_2016_')

# 全国居民消费价格分类指数（上年同月=100）（-2015）
def crawlMonthlyCPIYoY_2015():
  crawlStatsData('hgyd', 'A010102', '-2015', 'monthly_cpi_yoy_2015')
