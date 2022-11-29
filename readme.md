## 数据源列表

1. CFETS人民币汇率指数
http://www.chinamoney.com.cn/chinese/bkrmbidx/

2. 居民消费价格指数(上月=100)
https://data.stats.gov.cn/easyquery.htm

3. 货币供应
http://data.eastmoney.com/cjsj/hbgyl.html

4. 社融

5. 美元指数

6. 超储

7. 货币净投放与净回笼
http://www.chinamoney.com.cn/chinese/hb/

8. 回购定盘利率和银银间回购定盘利率
http://www.chinamoney.com.cn/chinese/bkfrr/

9. 国债及其他债券收益率曲线

https://www.chinabond.com.cn/cb/cn/zzsj/cywj/syqx/sjxz/zzgzqx/list.shtml
https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/historyQuery?startDate=2019-09-15&endDate=2020-09-15&gjqx=0&qxId=hzsylqx&locale=cn_ZH&mark=1

## chromedriver
https://npm.taobao.org/mirrors/chromedriver/


## akshare
https://www.akshare.xyz/

## 命令
pipenv run python **.py
pipenv install ** --pypi-mirror https://mirrors.aliyun.com/pypi/simple/
pipenv run python -m ipykernel install --user --name variousData --display-name variousData
pipenv run jupyter-lab
pipenv run  uvicorn src.web.backEnd.main:app --reload --port 8000