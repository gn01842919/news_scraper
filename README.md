# news_scrapper
從網路抓取新聞，篩選出感興趣的新聞，並存入資料庫中。需搭配另一專案 [db_operation_api](https://github.com/gn01842919/db_operation_api)，並建議搭配專案 [news_scraper](https://github.com/gn01842919/news_scraper) 使用。


## 主要功能:
讀取以下 RSS 來源:
- Google News
- Yahoo News

抓取當中的新聞標題、連結、發布時間，以及新聞內容，並根據規則檔篩選，儲存到資料庫中。

以 [Google World News](https://news.google.com/news/rss/headlines/section/topic/WORLD?ned=zh-tw_tw&hl=zh-tw&gl=TW) RSS 來源為例，當中每條新聞的 description 並不包含新聞的內容，而是三個報導同一條新聞的來源原始網站。
此程式會從中選一，爬取原始新聞內文，並以新聞內文根據規則檔中的設定，給予每個新聞一個代表「相關性」的分數。若一個 <新聞，規則> 對應的分數為大於零，代表該規則認為該新聞為「相關」或「感興趣」。


## 使用方法:
1. 安裝並設定 PostgreSQL。

2. 下載另一專案 [my_focus_news](https://github.com/gn01842919/my_focus_news) 並用其 manage.py 建立資料庫結構:
    1. `git clone https://github.com/gn01842919/my_focus_news.git`
    2. `pip install -r my_focus_news/deployment/requirements.txt`
    3. `python my_focus_news/manage.py migrate`

3. 下載此專案，以及 [db_operation_api](https://github.com/gn01842919/db_operation_api) :
    1. `git clone https://github.com/gn01842919/news_scraper.git`
    2. `pip install -r news_scraper/requirements.txt`
    3. `cd news_scraper/ ; git clone https://github.com/gn01842919/db_operation_api.git`

4. 撰寫規則檔 [rule.json](./rule.json)
    - 設定檔為 JSON 格式。

5. 依環境調整設定檔 [settings.py](./settings.py)

6. `python collect_news_to_db.py`
    - 若要以排程執行，可改用 `python schedule.py`，預設為每小時執行一次。


## To-Do:
- 擴充設定檔:
    * 防止 exclude 屬性擋掉太多東西，例如只在內文出現一次的話，可以考慮放過他。
        * 用另一個屬性，叫 ensure_times_lower 之類的，設定最高允許次數。
        * 但是如果出現在標題，還是把它排除掉。

    * 目前的 include 彼此之間一定要是 AND 關係，只要有一個關鍵字沒出現，該 RULE 就不會給分。
        * 增加屬性: include_any
        * 或允許多個 include 屬性，單個裡面的 Keyword 是 AND 關係，而 include 屬性彼此之間為 OR 關係。

- 測試程式
    * news_scraper
        * 完整 Unit Test 有點不容易，至少寫個 Functional Test。

- Yahoo 新聞來源比照 Google ，去抓原始的 local 新聞內容。
    * 對於 Yahoo RSS 的新聞來源，我目前是採用 Feed 中的 description 作為新聞內容，就沒有再去抓她的 local 原始新聞。主因是 Yahoo 並沒有直接提供這新聞是從哪裡來的，要找出規則可能要花不少力氣。也因為 Yahoo 的 description 大多已經是新聞內容的第一段，作為判斷關鍵字的依據也算堪用了。
    * 與 Yahoo 不同的是，Google 新聞的 descripiton 幾乎都只有新聞的第一句話，因此不得不去抓原始新聞內容，而且 Google 提供了他真正的新聞來源，甚至提供了三個來自不同新聞來源的同個新聞。

- 擴充可以處理的 local news 來源。

- 有些新聞來源用程式抓取時遇到 403 錯誤，但我人工查看網頁卻正常。也許是需要載入 Javascript?
  例子: https://www.thenewslens.com/article/90959

- 應能接受多個 rule 檔案。

- 可由 news_scraper 建立所需的資料庫結構，讓此專案不必依賴 [news_scraper](https://github.com/gn01842919/news_scraper) 。
