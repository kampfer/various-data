from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import traceback

driver = webdriver.Edge()

def init():
    driver.switch_to.default_content()

    driver.get('http://218.60.150.124/Kns55/Navi/NewItem.aspx?NaviID=25&BaseID=CZJB&BaseName=%e4%b8%ad%e5%9b%bd%e8%af%81%e5%88%b8%e6%8a%a5&NaviLink=-%2fKns55%2fNavi%2fNewNaviList.aspx%3fNaviID%3d25%26SearchFlg%3d1%26Field%3dchname%253B%25E5%258E%259F%25E5%2588%258A%25E5%2590%258D%25E7%25A7%25B0%257C%2525%2527%257B0%257D%2527%252C%253D%2527*%257B0%257D%2527%26Value%3d%25E4%25B8%25AD%25E5%259B%25BD%25E8%25AF%2581%25E5%2588%25B8%25E6%258A%25A5%26SelectIndex%3d0%7c%e4%b8%ad%e5%9b%bd%e8%af%81%e5%88%b8%e6%8a%a5&&SearchFlg=1&Field=chname%3B%E5%8E%9F%E5%88%8A%E5%90%8D%E7%A7%B0%7C%25%27%7B0%7D%27%2C%3D%27*%7B0%7D%27&Value=%E4%B8%AD%E5%9B%BD%E8%AF%81%E5%88%B8%E6%8A%A5&SelectIndex=0')

    startInput = driver.find_element(By.ID, 'publishdate_from')
    startInput.clear()
    startInput.send_keys('2015-1-1')
    endInput = driver.find_element(By.ID, 'publishdate_to')
    endInput.clear()
    endInput.send_keys('2015-12-31')

    driver.find_element(By.ID, 'btnSearch').click()

    driver.switch_to.frame('iframeResult')
    # total = init(driver.find_element(By.CLASS_NAME, 'biggerCss').text)
    totalSpan = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'biggerCss'))
    )
    total = int(totalSpan.text[1:])

    return total

def crawlNews(data):

    try:
        form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'ctl00'))
        )
    except:
        print('ctl00 error')
    else:
        rows = form.find_elements(By.CSS_SELECTOR, '.GridTableContent > tbody > tr:not(.GTTitle)')

        for row in rows:
            cols = row.find_elements(By.CSS_SELECTOR, 'td')
            col = {
                'title': cols[2].text,
                'author': cols[3].text,
                'source': cols[4].text,
                'date': cols[5].text,
                'url': cols[2].find_element(By.TAG_NAME, 'a').get_attribute('href')
            }
            data.append(col)

cur = 1
data = []

try:
    total = init()
    while (cur <= total):
        input = driver.find_element(By.CSS_SELECTOR, 'input[name="curpage1"]')
        input.clear()
        input.send_keys(str(cur))
        driver.find_element(By.CSS_SELECTOR, 'span.biggerCss + a').click()
        print(f'第{cur}页')
        crawlNews(data)
        cur += 1
        if (cur % 200 == 0):
            init()
except Exception as e:
    print(e)
    traceback.print_exc()
finally:
    df = pd.DataFrame(data)
    df.to_csv('./financeNews.csv')
    driver.quit()
