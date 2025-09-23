```mermaid
Diagram
    PODCAST_GROUP ||--|{ PODCAST_GROUP_PRESENTER : "has"
    PODCAST_GROUP ||--|{ EPISODE : "produces"
    PODCAST_GROUP ||--|| WRITER : "uses"
    PODCAST_GROUP ||--|{ NEWS_FEED_ASSIGNMENT : "assigned to"
    PODCAST_GROUP }|..|{ NEWS_FEED : "consumes"

    PODCAST_GROUP_PRESENTER }|..|{ PRESENTER : "references"
    EPISODE }|..|{ EPISODE_METADATA : "stores"
    EPISODE }|..|{ AUDIO_FILE : "produces"
    EPISODE }|..|{ EPISODE_ARTICLE_LINK : "links"
    EPISODE_ARTICLE_LINK }|..|{ ARTICLE : "references"

    NEWS_FEED ||--|{ ARTICLE : "contains"

    %% Attributes
    PODCAST_GROUP {
        uuid id PK
        string name
        text description
        string category
        string subcategory
        string language
        string country
        string[] tags
        string[] keywords
        string schedule   // cron‑like
        enum status
    }
    PRESENTER {
        uuid id PK
        string name
        text bio
        int age
        string gender
        json demographics
        json biases
        string[] specialties
        string[] expertise
        string[] interests
        string country
        string city
    }
    WRITER {
        uuid id PK
        string model   // fixed=Ollama
    }
    NEWS_FEED {
        uuid id PK
        string source_url
        enum type  // RSS or MCP
        datetime last_fetched
    }
    ARTICLE {
        uuid id PK
        string title
        string link
        text summary
        datetime publish_date
    }
    EPISODE {
        uuid id PK
        uuid group_id FK
        text script
        datetime created_at
        enum status   // draft, voiced, published
    }
    EPISODE_METADATA {
        uuid episode_id PK,F K
        string title
        text description
        string[] tags
        string[] keywords
        string category
        string subcategory
        string language
        string country
    }
    AUDIO_FILE {
        uuid episode_id PK,F K
        string url   // blob storage location
        int duration_seconds
    }
    PODCAST_GROUP_PRESENTER {
        uuid group_id PK,F K
        uuid presenter_id PK,F K
        int order   // 1‑4
    }
    PODCAST_GROUP_PRESENTER_ASSIGNMENT {
        uuid group_id PK,F K
        uuid presenter_id PK,F K
    }
    NEWS_FEED_ASSIGNMENT {
        uuid group_id PK,F K
        uuid feed_id PK,F K
    }
    EPISODE_ARTICLE_LINK {
        uuid episode_id PK,F K
        uuid article_id PK,F K
    }
```