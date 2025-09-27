# Service Visualization

## Overview

This document defines how to visualize the 9 core services of the Podcast AI application in a futuristic, real-time monitoring interface.

## Service Architecture Visualization

### 1. Service Flow Diagram

**Purpose**: Show the complete data flow through all services

**Visual Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    Podcast AI Service Flow                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [RSS Feeds] → [News Feed] → [Reviewer] → [Collections]        │
│       ↓              ↓           ↓            ↓                │
│  [External]    [Port 8001]  [Port 8007]  [Port 8008]          │
│                                                                 │
│       ↓              ↓           ↓            ↓                │
│  [AI Overseer] ← [Text Gen] ← [Writer] ← [Presenter]           │
│  [Port 8006]   [Port 8002]  [Port 8003]  [Port 8004]          │
│       ↓                                                         │
│  [Publishing] ← [API Gateway]                                  │
│  [Port 8005]   [Port 8000]                                     │
│       ↓                                                         │
│  [Local Host]                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Individual Service Cards

#### 2.1 API Gateway (Port 8000)
**Role**: Central entry point and admin interface
**Visual Elements**:
- Shield icon with neon blue glow
- Request/response metrics
- Authentication status
- Rate limiting indicators

**Key Metrics**:
- Requests per minute
- Average response time
- Active connections
- Authentication success rate

**Status Indicators**:
- Green: All endpoints responding
- Yellow: High latency or rate limiting
- Red: Service unavailable or errors

#### 2.2 News Feed Service (Port 8001)
**Role**: RSS/MCP feed fetching and article storage
**Visual Elements**:
- RSS feed icon with animated waves
- Feed health indicators
- Article processing queue
- Fetch success rate

**Key Metrics**:
- Active feeds count
- Articles fetched per hour
- Processing queue length
- Feed error rate

**Status Indicators**:
- Green: All feeds healthy, queue processing
- Yellow: Some feeds failing, queue building
- Red: Service down or major feed failures

#### 2.3 Text Generation Service (Port 8002)
**Role**: Script generation using Ollama
**Visual Elements**:
- Brain icon with neural network animation
- Generation progress bars
- Model status indicators
- Queue processing visualization

**Key Metrics**:
- Scripts generated per hour
- Average generation time
- Model response time
- Queue length

**Status Indicators**:
- Green: Model loaded, generating scripts
- Yellow: Model loading or high queue
- Red: Model unavailable or generation errors

#### 2.4 Writer Service (Port 8003)
**Role**: Episode metadata generation using Ollama
**Visual Elements**:
- Pen icon with writing animation
- Metadata generation progress
- Quality score indicators
- Processing timeline

**Key Metrics**:
- Metadata generated per hour
- Average processing time
- Quality scores
- Error rate

**Status Indicators**:
- Green: Generating metadata successfully
- Yellow: Processing delays or quality issues
- Red: Service errors or model failures

#### 2.5 Presenter Service (Port 8004)
**Role**: Text-to-speech using VibeVoice-1.5B
**Visual Elements**:
- Microphone icon with sound waves
- Audio generation progress
- Voice model status
- File processing indicators

**Key Metrics**:
- Audio files generated per hour
- Average generation time
- File sizes
- Quality metrics

**Status Indicators**:
- Green: VibeVoice model active, generating audio
- Yellow: Model loading or processing delays
- Red: Model unavailable or generation failures

#### 2.6 Publishing Service (Port 8005)
**Role**: Publishing to podcast hosting platforms
**Visual Elements**:
- Upload icon with progress indicators
- Platform status indicators
- Publishing queue visualization
- Success/failure rates

**Key Metrics**:
- Episodes published per hour
- Platform success rates
- Queue length
- Error rates

**Status Indicators**:
- Green: All platforms accessible, publishing successfully
- Yellow: Some platforms unavailable or delays
- Red: Publishing service down or platform failures

#### 2.7 AI Overseer Service (Port 8006)
**Role**: Central orchestrator and scheduler
**Visual Elements**:
- Command center icon with control panels
- Workflow status indicators
- Scheduling timeline
- Orchestration metrics

**Key Metrics**:
- Episodes orchestrated per day
- Workflow success rate
- Schedule adherence
- Error recovery rate

**Status Indicators**:
- Green: All workflows running smoothly
- Yellow: Some workflows delayed or issues
- Red: Orchestration failures or service down

#### 2.8 Reviewer Service (Port 8007)
**Role**: Article categorization and classification
**Visual Elements**:
- Magnifying glass icon with analysis animation
- Classification accuracy indicators
- Processing queue visualization
- Quality metrics

**Key Metrics**:
- Articles reviewed per hour
- Classification accuracy
- Processing time
- Queue length

**Status Indicators**:
- Green: High accuracy, processing efficiently
- Yellow: Accuracy issues or processing delays
- Red: Service errors or model failures

#### 2.9 Collections Service (Port 8008)
**Role**: Content management and organization
**Visual Elements**:
- Folder icon with organization animation
- Collection status indicators
- Content organization metrics
- Storage utilization

**Key Metrics**:
- Collections managed
- Content organization rate
- Storage usage
- Access patterns

**Status Indicators**:
- Green: Efficiently organizing content
- Yellow: Organization delays or storage issues
- Red: Service errors or storage failures

### 3. Real-time Monitoring Dashboard

#### 3.1 System Overview
**Layout**: 3x3 grid of service cards
**Features**:
- Real-time status updates
- Click-to-expand details
- Quick action buttons
- Performance metrics

#### 3.2 Service Details Panel
**Purpose**: Detailed view of individual service
**Content**:
- Service configuration
- Performance graphs
- Log entries
- Control actions

#### 3.3 Workflow Visualization
**Purpose**: Show end-to-end podcast generation process
**Visual Elements**:
- Animated workflow diagram
- Progress indicators
- Data flow arrows
- Status updates

### 4. Performance Metrics

#### 4.1 Response Time Monitoring
**Visualization**: Line chart with real-time updates
**Metrics**:
- Average response time
- 95th percentile
- Maximum response time
- Trend analysis

#### 4.2 Throughput Monitoring
**Visualization**: Bar chart with hourly/daily views
**Metrics**:
- Requests per second
- Episodes generated per hour
- Articles processed per minute
- Audio files created per hour

#### 4.3 Error Rate Tracking
**Visualization**: Gauge chart with color coding
**Metrics**:
- Error percentage
- Error types
- Recovery time
- Trend analysis

### 5. Alert System

#### 5.1 Service Health Alerts
**Types**:
- Service down
- High error rate
- Performance degradation
- Resource exhaustion

#### 5.2 Visual Alert Indicators
**Design**:
- Pulsing red border for critical
- Flashing yellow for warning
- Steady green for healthy
- Animated icons for attention

#### 5.3 Alert Management
**Features**:
- Acknowledge alerts
- Set custom thresholds
- Configure notifications
- Alert history

### 6. Interactive Features

#### 6.1 Service Control
**Actions**:
- Start/stop services
- Restart services
- Scale services
- Configure settings

#### 6.2 Real-time Updates
**Features**:
- WebSocket connections
- Auto-refresh intervals
- Manual refresh button
- Update notifications

#### 6.3 Filtering and Search
**Capabilities**:
- Filter by service status
- Search service names
- Sort by metrics
- Custom views

### 7. Mobile Responsiveness

#### 7.1 Mobile Layout
**Adaptations**:
- Single column layout
- Collapsible service cards
- Touch-friendly controls
- Swipe gestures

#### 7.2 Tablet Layout
**Adaptations**:
- Two-column layout
- Larger touch targets
- Optimized spacing
- Landscape support

### 8. Accessibility Features

#### 8.1 Screen Reader Support
**Features**:
- Semantic HTML structure
- ARIA labels
- Status announcements
- Keyboard navigation

#### 8.2 Visual Accessibility
**Features**:
- High contrast mode
- Colorblind-friendly indicators
- Scalable text
- Reduced motion options

### 9. Implementation Considerations

#### 9.1 Performance
**Optimizations**:
- Lazy loading of service details
- Efficient data updates
- Caching strategies
- Minimal DOM updates

#### 9.2 Scalability
**Features**:
- Modular component design
- Configurable service lists
- Dynamic service discovery
- Extensible metrics

#### 9.3 Security
**Considerations**:
- Secure WebSocket connections
- Authentication for controls
- Rate limiting
- Audit logging
