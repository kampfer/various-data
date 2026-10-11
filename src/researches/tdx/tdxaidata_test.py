from tdxaidata import tqs

# data = tqs.get_market_data(
#     field_list=["Open", "High", "Low", "Close"],
#     stock_list=["600000.SH"],
#     period="1d",
#     start_time="2025-01-01",
#     end_time="2025-01-31",
# )

# print(data)
# 一分钟周期云获取方式后期不做限制 不受限100天

data_divid_factors=tqs.get_divid_factors("600000.SH", "", "")
print(data_divid_factors)