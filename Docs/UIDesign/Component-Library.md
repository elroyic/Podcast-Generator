# Component Library

## Overview

This document defines the reusable UI components for the Podcast AI futuristic interface. All components follow the established color palette and typography guidelines.

## Core Components

### 1. Service Status Card

**Purpose**: Display individual service health and status

**Visual Design**:
- Dark card background (`#1a1a1a`) with subtle border
- Neon accent border that changes color based on status
- Glowing effect for active/processing states
- Animated status indicator

**States**:
- **Healthy**: Green neon border, pulsing glow
- **Processing**: Purple neon border, animated progress
- **Warning**: Orange neon border, slow pulse
- **Error**: Red neon border, rapid pulse
- **Idle**: Gray border, no animation

**Content**:
- Service name and icon
- Status indicator with animation
- Last activity timestamp
- Performance metrics (response time, CPU usage)
- Quick action buttons

```html
<div class="service-card service-status-healthy">
  <div class="service-header">
    <div class="service-icon">
      <svg><!-- Service-specific icon --></svg>
    </div>
    <div class="service-info">
      <h3 class="service-name">API Gateway</h3>
      <span class="service-status">Healthy</span>
    </div>
  </div>
  <div class="service-metrics">
    <div class="metric">
      <span class="metric-label">Response Time</span>
      <span class="metric-value">45ms</span>
    </div>
    <div class="metric">
      <span class="metric-label">CPU Usage</span>
      <span class="metric-value">12%</span>
    </div>
  </div>
  <div class="service-actions">
    <button class="btn-secondary">Restart</button>
    <button class="btn-primary">View Logs</button>
  </div>
</div>
```

### 2. Processor Animation

**Purpose**: Visual representation of AI processing workflows

**Visual Design**:
- Animated circuit-like pathways
- Flowing data particles
- Glowing connection nodes
- Real-time status updates

**Animation States**:
- **Idle**: Static circuit, dim glow
- **Processing**: Flowing particles, bright glow
- **Complete**: Success pulse, green accent
- **Error**: Red pulse, broken connection

**Implementation**:
- SVG-based animations for scalability
- CSS keyframes for smooth transitions
- JavaScript for real-time updates

```html
<div class="processor-animation">
  <svg class="circuit-diagram" viewBox="0 0 400 300">
    <!-- Circuit paths -->
    <path class="circuit-path" d="M50,150 Q200,50 350,150" />
    <path class="circuit-path" d="M50,150 Q200,250 350,150" />
    
    <!-- Processing nodes -->
    <circle class="processing-node" cx="100" cy="150" r="8" />
    <circle class="processing-node" cx="200" cy="150" r="8" />
    <circle class="processing-node" cx="300" cy="150" r="8" />
    
    <!-- Data particles -->
    <circle class="data-particle" cx="50" cy="150" r="3" />
  </svg>
  
  <div class="processor-status">
    <span class="status-label">Processing</span>
    <div class="progress-bar">
      <div class="progress-fill" style="width: 65%"></div>
    </div>
  </div>
</div>
```

### 3. Dashboard Grid

**Purpose**: Responsive layout for service cards and visualizations

**Layout**:
- CSS Grid-based responsive design
- Auto-adjusting columns based on screen size
- Consistent spacing and alignment
- Smooth transitions between layouts

**Breakpoints**:
- **Mobile**: 1 column
- **Tablet**: 2 columns
- **Desktop**: 3 columns
- **Large Desktop**: 4 columns

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  padding: 24px;
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 16px;
  }
}
```

### 4. Navigation Header

**Purpose**: Main navigation with service overview

**Visual Design**:
- Dark header with neon accent line
- Animated logo with subtle glow
- Service status summary
- Quick action buttons

**Features**:
- Real-time service count
- System health indicator
- Quick access to settings
- User profile dropdown

```html
<header class="main-header">
  <div class="header-left">
    <div class="logo">
      <svg class="logo-icon"><!-- Podcast AI logo --></svg>
      <span class="logo-text">Podcast AI</span>
    </div>
  </div>
  
  <div class="header-center">
    <div class="service-summary">
      <span class="summary-text">8/9 Services Healthy</span>
      <div class="health-indicator">
        <div class="health-bar">
          <div class="health-fill" style="width: 89%"></div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="header-right">
    <button class="btn-icon" title="Settings">
      <svg><!-- Settings icon --></svg>
    </button>
    <button class="btn-icon" title="Notifications">
      <svg><!-- Bell icon --></svg>
    </button>
  </div>
</header>
```

### 5. Data Visualization Components

#### 5.1 Real-time Metrics Chart

**Purpose**: Display performance metrics over time

**Visual Design**:
- Dark background with neon grid lines
- Animated data points
- Smooth line transitions
- Interactive tooltips

**Chart Types**:
- Line charts for trends
- Bar charts for comparisons
- Gauge charts for single metrics
- Heat maps for service distribution

#### 5.2 Service Flow Diagram

**Purpose**: Visualize data flow between services

**Visual Design**:
- Animated arrows showing data flow
- Service nodes with status indicators
- Real-time updates
- Interactive zoom and pan

### 6. Interactive Elements

#### 6.1 Buttons

**Primary Button**:
- Neon blue background (`#00d4ff`)
- Dark text (`#0a0a0a`)
- Hover glow effect
- Smooth transitions

**Secondary Button**:
- Transparent background
- Neon blue border and text
- Hover fill effect
- Consistent sizing

**Icon Button**:
- Circular design
- Icon-only content
- Hover scale effect
- Tooltip support

#### 6.2 Form Elements

**Input Fields**:
- Dark background with neon border
- Floating labels
- Focus glow effect
- Error state styling

**Select Dropdowns**:
- Dark theme
- Neon accent colors
- Smooth animations
- Search functionality

### 7. Loading States

#### 7.1 Skeleton Loaders

**Purpose**: Show loading state while data is being fetched

**Visual Design**:
- Animated shimmer effect
- Placeholder shapes matching content
- Subtle glow animation
- Smooth transitions

#### 7.2 Progress Indicators

**Purpose**: Show progress of long-running operations

**Visual Design**:
- Animated progress bars
- Percentage display
- Status messages
- Cancel functionality

### 8. Notification System

#### 8.1 Toast Notifications

**Purpose**: Show system alerts and updates

**Visual Design**:
- Slide-in animation
- Neon accent colors
- Auto-dismiss functionality
- Action buttons

**Types**:
- **Success**: Green neon (`#00ff88`)
- **Warning**: Orange neon (`#ff6b35`)
- **Error**: Red neon (`#ff3366`)
- **Info**: Blue neon (`#00d4ff`)

#### 8.2 Modal Dialogs

**Purpose**: Show detailed information or confirmations

**Visual Design**:
- Dark overlay background
- Centered content panel
- Neon border accent
- Smooth fade animations

### 9. Responsive Design

#### 9.1 Mobile Adaptations

- Collapsible navigation
- Stacked service cards
- Touch-friendly buttons
- Swipe gestures

#### 9.2 Tablet Adaptations

- Two-column layout
- Larger touch targets
- Optimized spacing
- Landscape orientation support

### 10. AI Generation Components

#### 10.1 AI Generation Modal

**Purpose**: Interface for generating podcast groups and presenter personas using AI

**Visual Design**:
- Dark modal overlay with neon border
- Animated AI processing indicators
- Step-by-step generation progress
- Real-time generation status

**Features**:
- Podcast group generation with AI
- Presenter persona creation
- Category and topic selection
- Generation progress tracking
- Preview and customization options

```html
<div class="ai-generation-modal">
  <div class="modal-overlay">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">🤖 AI Generation Studio</h2>
        <button class="modal-close">&times;</button>
      </div>
      
      <div class="generation-tabs">
        <button class="tab-btn active" data-tab="group">Podcast Group</button>
        <button class="tab-btn" data-tab="presenter">Presenter Persona</button>
      </div>
      
      <div class="generation-content">
        <!-- Group Generation Form -->
        <div class="tab-content active" id="group-tab">
          <div class="form-group">
            <label>Category</label>
            <select class="form-select">
              <option>Technology</option>
              <option>Business</option>
              <option>Science</option>
              <option>Entertainment</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Target Audience</label>
            <input type="text" class="form-input" placeholder="e.g., Tech professionals, Students">
          </div>
          
          <div class="form-group">
            <label>Podcast Style</label>
            <div class="style-options">
              <label class="radio-option">
                <input type="radio" name="style" value="informative">
                <span>Informative</span>
              </label>
              <label class="radio-option">
                <input type="radio" name="style" value="conversational">
                <span>Conversational</span>
              </label>
              <label class="radio-option">
                <input type="radio" name="style" value="entertaining">
                <span>Entertaining</span>
              </label>
            </div>
          </div>
        </div>
        
        <!-- Presenter Generation Form -->
        <div class="tab-content" id="presenter-tab">
          <div class="form-group">
            <label>Presenter Type</label>
            <select class="form-select">
              <option>Host</option>
              <option>Co-host</option>
              <option>Expert</option>
              <option>Interviewer</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Personality Traits</label>
            <div class="trait-selector">
              <button class="trait-chip" data-trait="enthusiastic">Enthusiastic</button>
              <button class="trait-chip" data-trait="analytical">Analytical</button>
              <button class="trait-chip" data-trait="humorous">Humorous</button>
              <button class="trait-chip" data-trait="professional">Professional</button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="generation-actions">
        <button class="btn-secondary">Cancel</button>
        <button class="btn-primary ai-generate-btn">
          <span class="btn-icon">🤖</span>
          Generate with AI
        </button>
      </div>
    </div>
  </div>
</div>
```

#### 10.2 AI Generation Progress

**Purpose**: Show real-time progress of AI generation process

**Visual Design**:
- Animated progress bar with neon glow
- Step-by-step indicators
- AI processing animations
- Generation status messages

**States**:
- **Initializing**: Setting up generation parameters
- **Processing**: AI is generating content
- **Reviewing**: Generated content is being validated
- **Complete**: Generation finished successfully
- **Error**: Generation failed with error message

```html
<div class="ai-generation-progress">
  <div class="progress-header">
    <h3>🤖 AI Generation in Progress</h3>
    <span class="progress-status">Processing...</span>
  </div>
  
  <div class="progress-steps">
    <div class="step active">
      <div class="step-icon">⚙️</div>
      <div class="step-content">
        <span class="step-title">Initializing</span>
        <span class="step-description">Setting up generation parameters</span>
      </div>
    </div>
    
    <div class="step">
      <div class="step-icon">🧠</div>
      <div class="step-content">
        <span class="step-title">AI Processing</span>
        <span class="step-description">Generating content with AI</span>
      </div>
    </div>
    
    <div class="step">
      <div class="step-icon">✅</div>
      <div class="step-content">
        <span class="step-title">Reviewing</span>
        <span class="step-description">Validating generated content</span>
      </div>
    </div>
  </div>
  
  <div class="progress-bar">
    <div class="progress-fill" style="width: 45%"></div>
  </div>
  
  <div class="generation-details">
    <div class="detail-item">
      <span class="detail-label">Estimated Time:</span>
      <span class="detail-value">2-3 minutes</span>
    </div>
    <div class="detail-item">
      <span class="detail-label">Current Step:</span>
      <span class="detail-value">AI Processing</span>
    </div>
  </div>
</div>
```

#### 10.3 AI Generation Results

**Purpose**: Display and customize AI-generated content

**Visual Design**:
- Preview cards with generated content
- Edit and customization options
- Save and discard actions
- Quality indicators

**Content Types**:
- **Podcast Group**: Name, description, category, schedule
- **Presenter Persona**: Name, bio, personality, voice style
- **Configuration**: Settings, preferences, customization

```html
<div class="ai-generation-results">
  <div class="results-header">
    <h3>✨ AI Generation Complete</h3>
    <div class="quality-indicator">
      <span class="quality-score">Quality: 95%</span>
      <div class="quality-bar">
        <div class="quality-fill" style="width: 95%"></div>
      </div>
    </div>
  </div>
  
  <div class="results-content">
    <div class="result-card">
      <div class="card-header">
        <h4>Podcast Group</h4>
        <button class="edit-btn">✏️ Edit</button>
      </div>
      
      <div class="card-content">
        <div class="field-group">
          <label>Name</label>
          <input type="text" value="Tech Talk Weekly" class="field-input">
        </div>
        
        <div class="field-group">
          <label>Description</label>
          <textarea class="field-textarea">A weekly podcast covering the latest in technology, featuring expert interviews and industry insights.</textarea>
        </div>
        
        <div class="field-group">
          <label>Category</label>
          <select class="field-select">
            <option>Technology</option>
          </select>
        </div>
      </div>
    </div>
    
    <div class="result-card">
      <div class="card-header">
        <h4>Presenter Persona</h4>
        <button class="edit-btn">✏️ Edit</button>
      </div>
      
      <div class="card-content">
        <div class="field-group">
          <label>Name</label>
          <input type="text" value="Alex Chen" class="field-input">
        </div>
        
        <div class="field-group">
          <label>Bio</label>
          <textarea class="field-textarea">Tech enthusiast with 10+ years in software development. Passionate about emerging technologies and their impact on society.</textarea>
        </div>
        
        <div class="field-group">
          <label>Personality</label>
          <input type="text" value="Analytical, Enthusiastic, Professional" class="field-input">
        </div>
      </div>
    </div>
  </div>
  
  <div class="results-actions">
    <button class="btn-secondary">Regenerate</button>
    <button class="btn-secondary">Save Draft</button>
    <button class="btn-primary">Create & Deploy</button>
  </div>
</div>
```

#### 10.4 AI Generation History

**Purpose**: Track and manage AI generation history

**Visual Design**:
- Timeline view of generations
- Status indicators for each generation
- Quick actions for regenerating or editing
- Search and filter capabilities

**Features**:
- Generation timestamp and status
- Content preview
- Regeneration options
- Export capabilities

```html
<div class="ai-generation-history">
  <div class="history-header">
    <h3>📚 Generation History</h3>
    <div class="history-controls">
      <input type="search" placeholder="Search generations..." class="search-input">
      <select class="filter-select">
        <option>All Types</option>
        <option>Podcast Groups</option>
        <option>Presenters</option>
      </select>
    </div>
  </div>
  
  <div class="history-timeline">
    <div class="timeline-item">
      <div class="timeline-marker success"></div>
      <div class="timeline-content">
        <div class="item-header">
          <span class="item-type">Podcast Group</span>
          <span class="item-time">2 hours ago</span>
        </div>
        <div class="item-title">Tech Talk Weekly</div>
        <div class="item-description">Technology podcast with expert interviews</div>
        <div class="item-actions">
          <button class="action-btn">View</button>
          <button class="action-btn">Regenerate</button>
          <button class="action-btn">Edit</button>
        </div>
      </div>
    </div>
    
    <div class="timeline-item">
      <div class="timeline-marker success"></div>
      <div class="timeline-content">
        <div class="item-header">
          <span class="item-type">Presenter</span>
          <span class="item-time">3 hours ago</span>
        </div>
        <div class="item-title">Alex Chen</div>
        <div class="item-description">Tech enthusiast with analytical personality</div>
        <div class="item-actions">
          <button class="action-btn">View</button>
          <button class="action-btn">Regenerate</button>
          <button class="action-btn">Edit</button>
        </div>
      </div>
    </div>
  </div>
</div>
```

### 11. Animation Guidelines

#### 11.1 Timing Functions

- **Ease-out**: For entrances and appearances
- **Ease-in**: For exits and disappearances
- **Ease-in-out**: For state changes
- **Linear**: For continuous animations

#### 11.2 Duration Standards

- **Micro-interactions**: 150-300ms
- **State changes**: 300-500ms
- **Page transitions**: 500-800ms
- **Loading animations**: 1000-2000ms

#### 11.3 Performance Considerations

- Use CSS transforms for animations
- Avoid animating layout properties
- Implement will-change for smooth animations
- Provide reduced motion alternatives
