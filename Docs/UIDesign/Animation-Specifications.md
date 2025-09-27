# Animation Specifications

## Overview

This document defines the animation specifications for the Podcast AI futuristic interface, focusing on processor animations, service status indicators, and interactive elements.

## Animation Principles

### 1. Design Philosophy
- **Smooth and Fluid**: All animations should feel natural and responsive
- **Purposeful**: Every animation serves a functional purpose
- **Performance-First**: Optimized for 60fps on all devices
- **Accessible**: Respects user preferences for reduced motion

### 2. Performance Guidelines
- Use CSS transforms and opacity for animations
- Avoid animating layout properties (width, height, top, left)
- Implement `will-change` for elements that will animate
- Use `transform3d` to trigger hardware acceleration
- Keep animations under 300ms for micro-interactions

## Core Animations

### 1. Service Status Animations

#### 1.1 Health Status Pulse
**Purpose**: Indicate service health status
**Duration**: 2 seconds (infinite)
**Easing**: `ease-in-out`

```css
@keyframes health-pulse {
  0%, 100% { 
    opacity: 1; 
    transform: scale(1);
  }
  50% { 
    opacity: 0.7; 
    transform: scale(1.05);
  }
}

.service-status-healthy {
  animation: health-pulse 2s ease-in-out infinite;
}
```

#### 1.2 Processing Animation
**Purpose**: Show active processing state
**Duration**: 1.5 seconds (infinite)
**Easing**: `linear`

```css
@keyframes processing-rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.service-status-processing .status-icon {
  animation: processing-rotate 1.5s linear infinite;
}
```

#### 1.3 Error State Blink
**Purpose**: Draw attention to error states
**Duration**: 0.5 seconds (infinite)
**Easing**: `ease-in-out`

```css
@keyframes error-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.service-status-error {
  animation: error-blink 0.5s ease-in-out infinite;
}
```

### 2. Processor Workflow Animations

#### 2.1 Data Flow Animation
**Purpose**: Show data moving between services
**Duration**: 3 seconds (infinite)
**Easing**: `ease-in-out`

```css
@keyframes data-flow {
  0% { 
    transform: translateX(-100px);
    opacity: 0;
  }
  20% { 
    opacity: 1;
  }
  80% { 
    opacity: 1;
  }
  100% { 
    transform: translateX(100px);
    opacity: 0;
  }
}

.data-particle {
  animation: data-flow 3s ease-in-out infinite;
}
```

#### 2.2 Circuit Glow Animation
**Purpose**: Indicate active processing pathways
**Duration**: 2 seconds (infinite)
**Easing**: `ease-in-out`

```css
@keyframes circuit-glow {
  0%, 100% { 
    stroke-opacity: 0.3;
    filter: drop-shadow(0 0 5px var(--color-neon-blue));
  }
  50% { 
    stroke-opacity: 1;
    filter: drop-shadow(0 0 15px var(--color-neon-blue));
  }
}

.circuit-path {
  animation: circuit-glow 2s ease-in-out infinite;
}
```

#### 2.3 Processing Node Pulse
**Purpose**: Show active processing nodes
**Duration**: 1.8 seconds (infinite)
**Easing**: `ease-in-out`

```css
@keyframes node-pulse {
  0%, 100% { 
    r: 8;
    fill-opacity: 0.8;
  }
  50% { 
    r: 12;
    fill-opacity: 1;
  }
}

.processing-node {
  animation: node-pulse 1.8s ease-in-out infinite;
}
```

### 3. UI Element Animations

#### 3.1 Card Hover Effects
**Purpose**: Provide interactive feedback
**Duration**: 0.3 seconds
**Easing**: `ease-out`

```css
.service-card {
  transition: all 0.3s ease-out;
}

.service-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
}
```

#### 3.2 Button Interactions
**Purpose**: Enhance user interaction feedback
**Duration**: 0.2 seconds
**Easing**: `ease-out`

```css
.btn-primary {
  transition: all 0.2s ease-out;
}

.btn-primary:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
}

.btn-primary:active {
  transform: scale(0.98);
}
```

#### 3.3 Loading States
**Purpose**: Show loading progress
**Duration**: 1.5 seconds (infinite)
**Easing**: `linear`

```css
@keyframes loading-shimmer {
  0% { background-position: -200px 0; }
  100% { background-position: calc(200px + 100%) 0; }
}

.loading-skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-secondary) 0px,
    var(--color-bg-tertiary) 50px,
    var(--color-bg-secondary) 100px
  );
  background-size: 200px 100%;
  animation: loading-shimmer 1.5s linear infinite;
}
```

### 4. Page Transition Animations

#### 4.1 Fade In/Out
**Purpose**: Smooth page transitions
**Duration**: 0.4 seconds
**Easing**: `ease-in-out`

```css
@keyframes fade-in {
  0% { 
    opacity: 0;
    transform: translateY(20px);
  }
  100% { 
    opacity: 1;
    transform: translateY(0);
  }
}

.page-enter {
  animation: fade-in 0.4s ease-in-out;
}
```

#### 4.2 Slide Transitions
**Purpose**: Navigate between sections
**Duration**: 0.3 seconds
**Easing**: `ease-out`

```css
@keyframes slide-in-right {
  0% { 
    transform: translateX(100%);
    opacity: 0;
  }
  100% { 
    transform: translateX(0);
    opacity: 1;
  }
}

.slide-enter-right {
  animation: slide-in-right 0.3s ease-out;
}
```

### 5. Notification Animations

#### 5.1 Toast Notifications
**Purpose**: Show system alerts
**Duration**: 0.4 seconds (enter), 0.3 seconds (exit)
**Easing**: `ease-out` (enter), `ease-in` (exit)

```css
@keyframes toast-enter {
  0% { 
    transform: translateX(100%);
    opacity: 0;
  }
  100% { 
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes toast-exit {
  0% { 
    transform: translateX(0);
    opacity: 1;
  }
  100% { 
    transform: translateX(100%);
    opacity: 0;
  }
}

.toast-enter {
  animation: toast-enter 0.4s ease-out;
}

.toast-exit {
  animation: toast-exit 0.3s ease-in;
}
```

#### 5.2 Alert Pulse
**Purpose**: Draw attention to critical alerts
**Duration**: 1 second (infinite)
**Easing**: `ease-in-out`

```css
@keyframes alert-pulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(255, 51, 102, 0.7);
  }
  50% { 
    box-shadow: 0 0 0 10px rgba(255, 51, 102, 0);
  }
}

.alert-critical {
  animation: alert-pulse 1s ease-in-out infinite;
}
```

### 6. Data Visualization Animations

#### 6.1 Chart Animations
**Purpose**: Animate data visualization updates
**Duration**: 0.8 seconds
**Easing**: `ease-out`

```css
@keyframes chart-grow {
  0% { 
    transform: scaleY(0);
    transform-origin: bottom;
  }
  100% { 
    transform: scaleY(1);
  }
}

.chart-bar {
  animation: chart-grow 0.8s ease-out;
}
```

#### 6.2 Progress Bar Fill
**Purpose**: Show progress completion
**Duration**: 1.2 seconds
**Easing**: `ease-out`

```css
@keyframes progress-fill {
  0% { width: 0%; }
  100% { width: var(--progress-width); }
}

.progress-bar-fill {
  animation: progress-fill 1.2s ease-out;
}
```

### 7. Interactive Element Animations

#### 7.1 Modal Animations
**Purpose**: Smooth modal appearance
**Duration**: 0.3 seconds
**Easing**: `ease-out`

```css
@keyframes modal-enter {
  0% { 
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  100% { 
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-enter {
  animation: modal-enter 0.3s ease-out;
}
```

#### 7.2 Dropdown Animations
**Purpose**: Smooth dropdown expansion
**Duration**: 0.2 seconds
**Easing**: `ease-out`

```css
@keyframes dropdown-expand {
  0% { 
    opacity: 0;
    transform: scaleY(0);
    transform-origin: top;
  }
  100% { 
    opacity: 1;
    transform: scaleY(1);
  }
}

.dropdown-enter {
  animation: dropdown-expand 0.2s ease-out;
}
```

### 8. Performance Optimizations

#### 8.1 Hardware Acceleration
```css
.animated-element {
  will-change: transform, opacity;
  transform: translateZ(0); /* Force hardware acceleration */
}
```

#### 8.2 Reduced Motion Support
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

#### 8.3 Animation Performance Monitoring
```javascript
// Monitor animation performance
function monitorAnimationPerformance() {
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'measure') {
        console.log(`Animation: ${entry.name}, Duration: ${entry.duration}ms`);
      }
    }
  });
  
  observer.observe({ entryTypes: ['measure'] });
}
```

### 9. Animation Timing Standards

#### 9.1 Duration Guidelines
- **Micro-interactions**: 150-300ms
- **State changes**: 300-500ms
- **Page transitions**: 500-800ms
- **Loading animations**: 1000-2000ms
- **Continuous animations**: 2000-4000ms

#### 9.2 Easing Functions
- **Ease-out**: For entrances and appearances
- **Ease-in**: For exits and disappearances
- **Ease-in-out**: For state changes
- **Linear**: For continuous animations
- **Custom cubic-bezier**: For specific feel requirements

### 10. Implementation Examples

#### 10.1 CSS Animation Classes
```css
/* Utility classes for common animations */
.animate-fade-in { animation: fade-in 0.4s ease-out; }
.animate-slide-up { animation: slide-up 0.3s ease-out; }
.animate-pulse { animation: pulse 2s ease-in-out infinite; }
.animate-spin { animation: spin 1s linear infinite; }
```

#### 10.2 JavaScript Animation Control
```javascript
// Animation control utility
class AnimationController {
  static fadeIn(element, duration = 400) {
    element.style.opacity = '0';
    element.style.transition = `opacity ${duration}ms ease-out`;
    element.style.opacity = '1';
  }
  
  static slideUp(element, duration = 300) {
    element.style.transform = 'translateY(20px)';
    element.style.opacity = '0';
    element.style.transition = `all ${duration}ms ease-out`;
    element.style.transform = 'translateY(0)';
    element.style.opacity = '1';
  }
}
```

### 11. Testing and Validation

#### 11.1 Performance Testing
- Monitor frame rates during animations
- Test on various devices and browsers
- Validate accessibility compliance
- Check reduced motion preferences

#### 11.2 User Experience Testing
- Gather feedback on animation timing
- Test with different user groups
- Validate animation purposes
- Ensure animations enhance usability
