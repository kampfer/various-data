from utils import crawlStatsData

def crawlYearlyPriceFixingIndex():
  crawlStatsData('hgnd', 'A0902', '1990-', 'yearly_price_fix_index')