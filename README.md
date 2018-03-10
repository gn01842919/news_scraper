# news_scrapper

### 主要功能:
讀取以下 RSS 來源:
- Google News
- Yahoo News

抓取這些新聞的標題、連結、發布時間，以及新聞內容，儲存到資料庫中。

### 使用方法:
1. 建立好資料庫。(依賴於 my_focus_news)
2. python collect_news_to_db.py


### To-Do:
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

