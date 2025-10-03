# News Feed Enhancement - Quick Guide

## How to Use the Enhanced Article Details View

### Viewing Article Details

1. **Navigate to News Feed Dashboard**
   - Go to `http://localhost:8000/news-feed`
   - Or click "News Feed" in the navigation menu

2. **View Article Details** - Three ways:
   - Click anywhere on an article row
   - Click the "View" button on the right side
   - Entire article card is clickable

3. **Article Details Modal Shows**:

   ✅ **Extracted Article Content**
   - Full text extracted from the source
   - First 5000 characters shown for very long articles
   - Scrollable content area

   ✅ **Collection Assignment**
   - Shows which collection the article belongs to
   - "Not added to any collection yet" if unassigned
   - Link to view the collection

   ✅ **Review Tags**
   - All tags assigned by the AI reviewer
   - Color-coded badges for easy scanning
   - Only appears if tags exist

   ✅ **Reviewer Summary**
   - AI-generated summary of the article
   - Shows reviewer type (light or heavy)
   - Confidence score displayed
   - Only appears if article has been reviewed

   ✅ **Linked Podcasts**
   - Lists all podcast episodes that use this article
   - Shows episode status (draft, voiced, published)
   - Shows podcast group name
   - Creation date for tracking
   - "Not used in any podcast" if no links exist

   ✅ **Additional Information**
   - Article summary from RSS feed
   - Publication date
   - Feed source information
   - Processing timestamps
   - Article and Feed IDs

### Quick Actions

- **Close Modal**: Click X button or click outside the modal
- **View Original**: Click "View Original Article" link
- **Go to Collection**: Click "View Collection →" link
- **Access Feed**: Feed name and URL shown

## What Each Section Tells You

### Collection Section (Purple)
**Tells you**: Where this article is organized
**Use case**: Track content categorization and episode planning

### Tags Section (Blue)
**Tells you**: Topic keywords from AI analysis
**Use case**: Quick understanding of article themes, filtering, search

### Reviewer Summary (Green)
**Tells you**: AI's assessment of the article
**Use case**: Quality check, relevance scoring, content preview

### Linked Podcasts (Orange)
**Tells you**: Which episodes feature this article
**Use case**: Track content usage, avoid duplication, measure impact

### Extracted Content
**Tells you**: Actual article text (not just headline/summary)
**Use case**: Read full content without leaving admin panel, verify extraction quality

## Color Guide

- 🟣 **Purple** = Collections
- 🔵 **Blue** = Tags
- 🟢 **Green** = Reviewer Analysis
- 🟠 **Orange** = Podcast Episodes
- ⚫ **Gray** = Metadata & Info

## Keyboard Shortcuts

- `Esc` - Close modal (if focused)
- Click outside modal - Close modal
- Scroll wheel - Navigate long article content

## Tips

1. **Check Extraction Quality**: Look at the extracted content to verify the news-feed service is properly extracting article text

2. **Review Before Use**: Check the reviewer summary and tags before adding to a collection

3. **Track Usage**: Use the Linked Podcasts section to see how often an article is reused

4. **Monitor Collections**: Purple section helps you understand your content organization

5. **Quick Scanning**: Use tags for rapid topic identification

## Troubleshooting

**Modal won't open?**
- Check browser console for errors
- Verify article ID is valid
- Ensure API gateway is running

**Missing data in modal?**
- Some sections only appear if data exists
- Articles may not have reviewer data yet
- Collections are optional

**Content truncated?**
- Articles over 5000 chars show partial content
- Character count indicates full length
- Original article link always available

## API Endpoint

For developers integrating with the system:

```
GET /api/news-feed/articles/{article_id}
```

Returns comprehensive article details including:
- Basic article info
- Feed details
- Collection assignment
- Review tags and summary
- Linked episodes
- Processing metadata

