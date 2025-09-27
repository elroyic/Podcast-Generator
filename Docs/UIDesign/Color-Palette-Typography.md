# Color Palette & Typography

## Color Palette

### Primary Colors

#### Dark Backgrounds
- **Primary Dark**: `#0a0a0a` - Main background
- **Secondary Dark**: `#1a1a1a` - Card backgrounds, panels
- **Tertiary Dark**: `#2a2a2a` - Hover states, borders
- **Accent Dark**: `#1f1f1f` - Service containers

#### Neon Accent Colors
- **Electric Blue**: `#00d4ff` - Primary accent, active states
- **Cyber Green**: `#00ff88` - Success states, healthy services
- **Neon Purple**: `#8b5cf6` - Secondary accent, processing states
- **Warning Orange**: `#ff6b35` - Warning states, attention
- **Error Red**: `#ff3366` - Error states, failed services
- **Info Cyan**: `#06b6d4` - Information, metadata

#### Text Colors
- **Primary Text**: `#ffffff` - Main text, high contrast
- **Secondary Text**: `#b3b3b3` - Secondary information
- **Muted Text**: `#666666` - Disabled states, placeholders
- **Accent Text**: `#00d4ff` - Links, interactive elements

### Color Usage Guidelines

#### Service Status Colors
- **Healthy**: `#00ff88` (Cyber Green)
- **Processing**: `#8b5cf6` (Neon Purple)
- **Warning**: `#ff6b35` (Warning Orange)
- **Error**: `#ff3366` (Error Red)
- **Idle**: `#666666` (Muted Text)

#### Interactive Elements
- **Primary Button**: `#00d4ff` background, `#0a0a0a` text
- **Secondary Button**: `#2a2a2a` background, `#00d4ff` text
- **Hover State**: `#00b8e6` (darker blue)
- **Active State**: `#0099cc` (even darker blue)

## Typography

### Font Stack
```css
font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### Font Weights
- **Light**: 300 - Subtle text, metadata
- **Regular**: 400 - Body text, descriptions
- **Medium**: 500 - Labels, secondary headings
- **SemiBold**: 600 - Primary headings, important text
- **Bold**: 700 - Main titles, emphasis

### Font Sizes
- **Display Large**: 48px - Main page titles
- **Display Medium**: 36px - Section headers
- **Heading Large**: 24px - Card titles
- **Heading Medium**: 20px - Subsection headers
- **Body Large**: 16px - Primary body text
- **Body Medium**: 14px - Secondary text
- **Body Small**: 12px - Metadata, timestamps
- **Caption**: 10px - Labels, status indicators

### Line Heights
- **Tight**: 1.2 - Headings, titles
- **Normal**: 1.5 - Body text
- **Relaxed**: 1.6 - Long-form content

## Accessibility

### Contrast Ratios
- **Primary Text**: 4.5:1 minimum contrast ratio
- **Secondary Text**: 3:1 minimum contrast ratio
- **Interactive Elements**: 3:1 minimum contrast ratio
- **Focus Indicators**: 3:1 minimum contrast ratio

### Color Blindness Considerations
- Use patterns and icons alongside colors for status indication
- Ensure information is not conveyed by color alone
- Test with color blindness simulators

## Implementation

### CSS Custom Properties
```css
:root {
  /* Dark Backgrounds */
  --color-bg-primary: #0a0a0a;
  --color-bg-secondary: #1a1a1a;
  --color-bg-tertiary: #2a2a2a;
  --color-bg-accent: #1f1f1f;
  
  /* Neon Accents */
  --color-neon-blue: #00d4ff;
  --color-neon-green: #00ff88;
  --color-neon-purple: #8b5cf6;
  --color-warning-orange: #ff6b35;
  --color-error-red: #ff3366;
  --color-info-cyan: #06b6d4;
  
  /* Text Colors */
  --color-text-primary: #ffffff;
  --color-text-secondary: #b3b3b3;
  --color-text-muted: #666666;
  --color-text-accent: #00d4ff;
  
  /* Typography */
  --font-family-primary: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-weight-light: 300;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}
```

### Service Status Color Classes
```css
.service-status-healthy { color: var(--color-neon-green); }
.service-status-processing { color: var(--color-neon-purple); }
.service-status-warning { color: var(--color-warning-orange); }
.service-status-error { color: var(--color-error-red); }
.service-status-idle { color: var(--color-text-muted); }
```

## Visual Hierarchy

### Information Architecture
1. **Primary**: Service status, critical alerts
2. **Secondary**: Processing metrics, performance data
3. **Tertiary**: Configuration options, settings
4. **Quaternary**: Help text, metadata

### Visual Weight
- **Heavy**: Neon colors, bold typography, large elements
- **Medium**: Regular colors, medium typography, standard elements
- **Light**: Muted colors, light typography, subtle elements
