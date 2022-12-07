from utils import crawlStatsData

def crawlYearlyPriceFixingIndex():
  crawlStatsData('hgnd', 'A0902', '1990-', 'yearly_price_fix_index')

def crawlMonthlyCPIYoY2016_():
  crawlStatsData('hgyd', 'A010201', '2016-', 'monthly_cpi_yoy_2016_')

def crawlMonthlyCPIYoY_2015():
  crawlStatsData('hgyd', 'A010202', '-2015', 'monthly_cpi_yoy_2015')
