# Article Browser - Complete Guide

## Overview
The News Feed page now includes a powerful article browser that can handle viewing and managing thousands of articles with filtering, search, and pagination capabilities.

## Key Features

### 📊 Pagination
- **Default**: 50 articles per page
- **Options**: 25, 50, 100, or 200 per page
- **Navigation**: Previous/Next buttons with page counter
- **Display**: Shows "X to Y of Z total" articles

### 🔍 Advanced Filtering

#### Search
- **What it searches**: Article titles, summaries, and full content
- **How to use**: Type your query and press Enter or click "Apply Filters"
- **Example**: Search for "technology", "AI", "climate change"

#### Feed Filter
- **Purpose**: View articles from specific RSS feeds only
- **Options**: Dropdown populated with all your configured feeds
- **Use case**: Focus on content from particular sources

#### Reviewer Status Filter
- **Unreviewed**: Articles not yet processed by AI reviewer
- **Light Reviewed**: Articles processed by light reviewer
- **Heavy Reviewed**: Articles processed by heavy reviewer
- **Use case**: Quality control, workflow management

#### Collection Status Filter
- **In Collection**: Articles already assigned to collections
- **Not in Collection**: Articles available for assignment
- **Use case**: Find unprocessed content, avoid duplicates

### 📈 Real-Time Stats

The page displays:
- **Total Articles**: Grand total of all collected articles
- **Articles Today**: Number collected in last 24 hours
- **Active Feeds**: Number of enabled RSS feeds
- **Filtered Count**: Number matching current filters

## How to Use

### Basic Browsing

1. **Navigate to News Feed**
   - Go to `http://localhost:8000/news-feed`
   - Click "News Feed" in navigation menu

2. **View Articles**
   - Articles load automatically (first 50 shown)
   - Total count displayed at top
   - Click any article to view full details

3. **Navigate Pages**
   - Use Previous/Next buttons
   - Current page number shown
   - Buttons disabled when at first/last page

### Using Filters

1. **Open Filters Panel**
   - Click "Filters" button at top right
   - Panel slides down with all filter options

2. **Set Your Criteria**
   - Enter search terms (optional)
   - Select feed (optional)
   - Select reviewer status (optional)
   - Select collection status (optional)

3. **Apply**
   - Click "Apply Filters" button
   - Or press Enter in search box
   - Results update immediately

4. **Clear Filters**
   - Click "Clear" button to reset all filters
   - Returns to showing all articles

### Changing Page Size

1. Click the page size dropdown (bottom right)
2. Select: 25, 50, 100, or 200 articles per page
3. View automatically reloads with new page size

## Article Display

Each article shows:

### Primary Info
- **Title**: Full article headline
- **Feed**: Source feed name
- **Date**: Publication date

### Badges & Indicators
- **Collection Badge** (Purple): Shows collection name if assigned
- **Tags Badge** (Blue): Number of reviewer tags applied
- **Review Status** (Badge): Unreviewed / Light / Heavy
- **Confidence**: Percentage score (if reviewed)

### Actions
- **View Button**: Opens detailed modal
- **External Link**: Opens original article in new tab
- **Click Row**: Alternative way to view details

## Use Cases

### 1. Find Unprocessed Articles
```
Filter by: Reviewer Status = "Unreviewed"
Result: See all articles waiting for review
Action: Send to reviewer or assign to collection
```

### 2. Review Articles from Specific Feed
```
Filter by: Feed = "TechCrunch"
Result: All articles from TechCrunch
Action: Quality check, assign to tech podcast
```

### 3. Find Articles for Collection
```
Filter by: Collection Status = "Not in Collection"
         Reviewer Status = "Heavy Reviewed"
Result: High-quality articles ready for use
Action: Assign to podcast collections
```

### 4. Search Specific Topics
```
Search: "artificial intelligence"
Result: All articles mentioning AI
Action: Create AI-focused episode
```

### 5. Review Today's Content
```
Filter by: Date From = Today
Result: All articles collected today
Action: Daily content review workflow
```

## Performance Tips

### For Large Article Counts (1000+)

1. **Use Filters**: Don't load all articles at once
   - Filter by feed or review status first
   - Use search to narrow results

2. **Adjust Page Size**: 
   - Use 25-50 for quick browsing
   - Use 100-200 for batch operations

3. **Leverage Search**:
   - Search is indexed and fast
   - More specific = faster results

4. **Review by Feed**:
   - Process one feed at a time
   - Prevents overwhelming interface

## Keyboard Shortcuts

- **Enter** in search box → Apply filters
- **Esc** → Close detail modal (when focused)

## API Details

### Endpoint
```
GET /api/news-feed/articles
```

### Query Parameters
- `limit`: Articles per page (default: 50)
- `offset`: Starting position (default: 0)
- `feed_id`: UUID of specific feed
- `reviewer_type`: "unreviewed" | "light" | "heavy"
- `has_collection`: true | false
- `search`: Search term
- `date_from`: ISO datetime string
- `date_to`: ISO datetime string

### Response Format
```json
{
  "total": 1217,
  "offset": 0,
  "limit": 50,
  "articles": [
    {
      "id": "uuid",
      "title": "string",
      "feed_name": "string",
      "reviewer_type": "light",
      "review_tags": ["tag1", "tag2"],
      "collection_name": "Tech News",
      "confidence": 0.85,
      ...
    }
  ]
}
```

## Common Workflows

### Daily Review Process
1. Open News Feed page
2. Check "Articles Today" stat
3. Filter: Reviewer Status = "Unreviewed"
4. Review and tag articles
5. Assign high-quality to collections

### Content Planning
1. Filter: Collection Status = "Not in Collection"
2. Filter: Reviewer Status = "Heavy Reviewed"
3. Browse available content
4. Click articles to view full details
5. Assign to appropriate collections

### Quality Assurance
1. Filter: Reviewer Status = "Light Reviewed"
2. Filter: Confidence < 70%
3. Review flagged articles
4. Verify extraction quality
5. Manually re-assign if needed

### Feed Performance Check
1. Select specific feed from dropdown
2. Check article count and quality
3. Review recent articles
4. Adjust feed settings if needed

## Troubleshooting

### "No articles found"
- Check if filters are too restrictive
- Click "Clear" to reset filters
- Verify feeds are active and fetching

### Slow loading with large results
- Reduce page size to 25-50
- Add more specific filters
- Use search to narrow results

### Missing article details
- Some fields optional (tags, collection)
- Unreviewed articles won't have reviewer data
- Check if extraction succeeded

### Pagination not working
- Check browser console for errors
- Verify API is responding
- Try refreshing the page

## Best Practices

1. **Start with Filters**: Don't browse all 1000+ articles
2. **Use Search**: Fastest way to find specific content
3. **Process in Batches**: Use page size appropriate to task
4. **Regular Review**: Check unreviewed articles daily
5. **Feed-by-Feed**: Process one feed at a time
6. **Monitor Quality**: Use confidence scores
7. **Track Collections**: Use collection filter to avoid duplicates

## Future Enhancements

Planned features:
- Bulk selection and actions
- Export filtered results
- Saved filter presets
- Date range picker
- Sort by different fields
- Tag-based filtering
- Multi-select feeds
- Article comparison view
- Duplicate detection
- Advanced search syntax

