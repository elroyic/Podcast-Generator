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

### 10. Animation Guidelines

#### 10.1 Timing Functions

- **Ease-out**: For entrances and appearances
- **Ease-in**: For exits and disappearances
- **Ease-in-out**: For state changes
- **Linear**: For continuous animations

#### 10.2 Duration Standards

- **Micro-interactions**: 150-300ms
- **State changes**: 300-500ms
- **Page transitions**: 500-800ms
- **Loading animations**: 1000-2000ms

#### 10.3 Performance Considerations

- Use CSS transforms for animations
- Avoid animating layout properties
- Implement will-change for smooth animations
- Provide reduced motion alternatives
