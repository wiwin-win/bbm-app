
from playwright.sync_api import sync_playwright
p=sync_playwright().start()
b=p.chromium.launch(headless=True)
page=b.new_page(viewport={'width':1440,'height':900})
page.goto('http://localhost:8791/?nocache=1')
page.wait_for_timeout(2000)
page.screenshot(path='pratinjau-pc-nocache.png', full_page=True)
b.close()
p.stop()
print('done')
