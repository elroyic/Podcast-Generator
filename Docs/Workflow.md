# Updates and Enhancements to Application

## RSS News Services

**Feedback:** News service is limited with only a few RSS feeds on the list.  
**Action:** Add the following RSS feeds:

| #  | Feed Name                      | RSS URL                                                        |
|----|------------------------------- |--------------------------------------------------------------- |
| 1  | MarketWatch                    | https://feeds.content.dowjones.io/public/rss/marketwatch/markets |
| 2  | Investing.com                  | https://www.investing.com/rss/news.rss                         |
| 3  | CNBC                           | https://search.cnbc.com/rs/search/company-news/rss             |
| 4  | Seeking Alpha                  | https://seekingalpha.com/feed.xml                              |
| 5  | The Motley Fool UK             | https://www.fool.co.uk/feed                                    |
| 6  | INO.com Blog                   | https://ino.com/blog/feed                                      |
| 7  | AlphaStreet                    | https://news.alphastreet.com/feed                              |
| 8  | Raging Bull                    | https://ragingbull.com/feed                                    |
| 9  | Moneycontrol                   | https://www.moneycontrol.com/rss/latestnews.xml                |
| 10 | Scanz Blog                     | https://scanz.com/feed                                         |
| 11 | Market Screener                | https://www.marketscreener.com/rss                             |
| 12 | Investors Business Daily       | https://www.investors.com/Home/SliderRss                       |
| 13 | Yahoo Finance                  | https://finance.yahoo.com/rss                                  |
| 14 | IIFL Securities                | https://www.indiainfoline.com/news/rss                         |
| 15 | Nasdaq                         | https://www.nasdaq.com/feed/rss                                |
| 16 | Stock Market.com               | https://stockmarket.com/rss                                    |
| 17 | Equitymaster                   | https://www.equitymaster.com/feed                              |
| 18 | KlickAnalytics                 | https://klickanalytics.com/rss                                 |
| 19 | BBC News – Top Stories         | https://feeds.bbci.co.uk/news/rss.xml                          |
| 20 | CNN – Top Stories              | http://rss.cnn.com/rss/edition.rss                             |
| 21 | Reuters – World News           | http://feeds.reuters.com/Reuters/worldNews                     |
| 22 | The Guardian – World           | https://www.theguardian.com/world/rss                          |
| 23 | Al Jazeera – All News          | https://www.aljazeera.com/xml/rss/all.xml                      |
| 24 | Associated Press (AP)          | https://apnews.com/rss                                         |
| 25 | NPR News                       | https://feeds.npr.org/1001/rss.xml                             |
| 26 | DW News (Deutsche Welle)       | https://rss.dw.com/rdf/rss-en-all                              |
| 27 | Politico – Politics            | https://www.politico.com/rss/politics08.xml                    |
| 28 | New York Times – Home Page     | https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml      |
| 29 | Reuters Top News               | https://feeds.reuters.com/reuters/topNews                      |
| 30 | BBC News World                 | https://feeds.bbci.co.uk/news/world/rss.xml                    |
| 31 | The New York Times Home Page   | https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml      |
| 32 | Al Jazeera All News            | https://www.aljazeera.com/xml/rss/all.xml                      |
| 33 | Associated Press Top Stories   | https://apnews.com/rss                                         |
| 34 | NPR News Top Stories           | https://feeds.npr.org/1001/rss.xml                             |

---

## AI Overseer

- **Purpose:** Handle increased news volume by classifying, categorizing, and ranking news articles by importance.
- **Workflow:**
    1. **Feed Processing:**  
        - Each feed is sent to the **Reviewer** for categorization and classification.
        - After review, feeds are summarized and tagged (topic, subject, tags).
        - Feeds can belong to multiple **Collections**.
    2. **Collections:**  
        - Only sent to the **Writer** as per Podcast Group schedule.
        - Must contain at least 3 feeds and summaries before being sent to Writer.
        - If a collection is incomplete at scheduled time, the podcast is skipped for that cycle.
        - If skipped, Writer is notified to include an apology/excuse in the next episode.

### Podcast Group Management (by AI Overseer)

- **Each Podcast Group includes:**
    - Tags
    - Subjects
    - Schedule (Daily, Weekly, Monthly)
        - Scheduler must allow generation at a specific time.
        - No more than 1 release per day.
    - Collection (feeds reviewed and grouped)
    - Writer
    - Presenters (1–4, created per group, voices via VibeVoice)
    - Podcast Length

- **Script Flow:**
    - Once Editor returns the script, AI Overseer passes it to VibeVoice to generate the final `.mp3` file.

---

## Roles and Responsibilities

### Presenter (gpt-oss-20b)
- [Model](https://huggingface.co/openai/gpt-oss-20b)
- Each presenter has a unique persona and voice.
- Tasks:
    - Review collection for podcast episode.
    - Provide a 1000-word brief on the collection (in character).
    - Review the script from Writer and provide 500-word feedback.

### Writer (Qwen3)
- Receives a collection containing:
    - Feeds
    - Reviewer’s classifications and summaries
    - Presenter’s briefs
- Produces a podcast script of the required length.
- Passes script to Editor for final review and polish.

### Editor (Qwen3)
- Receives script and collection.
- Reviews for:
    - Length
    - Accuracy (must tie back to collection)
    - Engagement and entertainment value

### Reviewer (Qwen3)
- [Model](https://huggingface.co/Qwen/Qwen3-4B) ([docs](https://docs.vllm.ai/en/latest/))
- **Feed Processing:** Use queuing (not batching).
- **Feed Categories:**
    - Topic
    - Subject
    - Tags (e.g., Politics, Tech, Finance, AI, Trending)
    - Summary (≤500 characters)
    - Importance rank (1–10)

### Collections
- Belong to Podcast Group.
- Multiple collections can belong to a group.
- Contain:
    - Feeds
    - Reviewer output
    - Presenter output
    - Writer output

---

## Publishing

- To be focused on in future updates.

---

## Dashboard Enhancements

- **Visibility:** See running services and resource usage.
- **Controls:** Ability to rate limit, pause, or stop services.
- **Scaling:** Docker services should scale elastically (up to 5 CPUs per service). Workers managed from dashboard.

### Required Pages

- **Podcast Group Management**
    - View and edit all podcast groups.
    - Set schedules and edit fields.
- **Presenter Management**
    - Update presenter fields and persona.
    - Change prompt and LLM model (from installed Ollama models).
    - View stats (collection/script reviews).
- **Collections Management**
    - View and enter collections to see contents.
    - User-friendly expanding sidebar:
        - Level 1: Collection
            - Level 2: Contents (briefs, feeds, summaries, scripts, feedback, editor-reviewed script)
                - Level 3: File names
    - Selecting files displays them in the center frame (white text on black, Times New Roman).
- **Writer Management**
    - Update prompt and LLM model.
    - View stats (scripts written per day graph).
- **Reviewer Management**
    - Update prompt and LLM model.
    - View stats (feeds reviewed per day graph).
- **Editor Management**
    - Update prompt and LLM model.
    - View stats (feeds reviewed per day graph).
