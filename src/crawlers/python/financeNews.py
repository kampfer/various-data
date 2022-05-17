from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

driver = webdriver.Chrome()

# http://111.21.214.29/kns55/brief/result.aspx?dbPrefix=CCND

driver.get('https://kns.cnki.net/kns/brief/result.aspx?dbprefix=CCND')

startInput = driver.find_element_by_id('publishdate_from')
startInput.clear()
startInput.send_keys('2015-1-1')
endInput = driver.find_element_by_id('publishdate_to')
endInput.clear()
endInput.send_keys('2015-12-31')
sourceInput = driver.find_element_by_id('magazine_value1')
sourceInput.clear()
sourceInput.send_keys('中国证券报')

data = []

def crawlNews():

    try:
        form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'ctl00'))
        )
    except:
        print('error')
        time.sleep(60)
        driver.back()
        # crawlNews()
        driver.switch_to.frame('iframeResult')
    else:
        table = form.find_element_by_css_selector('.GridTableContent')
        rows = table.find_elements_by_css_selector('tr:not(.GTContentTitle)')

        for row in rows:
            cols = row.find_elements_by_tag_name('td')
            col = {
                'title': cols[1].text,
                'author': cols[2].text,
                'source': cols[3].text,
                'date': cols[4].text,
                'url': cols[1].find_element_by_tag_name('a').get_attribute('href')
            }
            data.append(col)

contextSwitched = False
next = driver.find_element_by_id('btnSearch')
while (next):
    next.click()
    if (not contextSwitched):
        contextSwitched = True
        driver.switch_to.frame('iframeResult')
    crawlNews()
    page = driver.find_element_by_css_selector('.pageBar_bottom')
    next = page.find_element_by_link_text('下一页')
    # time.sleep(10)

df = pd.DataFrame(data)
df.to_csv('./data/financeNews.csv')
