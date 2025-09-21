# SPA Hash Navigation Implementation

## Overview
Convert the existing single-page application to use URL hash fragments for tab navigation, enabling persistent URLs and client-side caching of clips data.

## Goals
1. **URL Persistence**: Stay on same tab when reloading page (`#clips`, `#settings`)
2. **Client-side Caching**: Preserve clips data when switching tabs (no server reload)
3. **Better UX**: Instant tab switching, browser back/forward support

## Technical Approach

### Hash Fragment Strategy
- Use `window.location.hash` to track current tab
- Hash values: `""` (home), `"#clips"`, `"#settings"`
- Listen for `hashchange` events to handle browser navigation

### Caching Strategy
- Store clips data in global JavaScript variables
- Only reload from server when explicitly requested (refresh button)
- Preserve filter states (cloud/local storage selection)

## Implementation Phases

### Phase 1: Basic Hash Navigation
**Goal**: URL changes with tab switching, page reload preserves tab

**Changes**:
- Modify tab click handlers to set `window.location.hash`
- Add `hashchange` event listener
- Implement `showTabFromHash()` function
- Update initial page load to check hash

**Files Modified**:
- `static/js/app.js`: Add hash handling functions
- `templates/index.html`: Update tab click handlers (if needed)

### Phase 2: Clips Data Caching
**Goal**: Eliminate server requests when switching between tabs

**Changes**:
- Create global clips cache object
- Modify `loadClips()` to use cache when available
- Add cache invalidation on explicit refresh
- Preserve storage type selection in cache

**Files Modified**:
- `static/js/clips.js`: Add caching logic
- `static/js/app.js`: Integrate cache with navigation

### Phase 3: Enhanced UX Features
**Goal**: Polish user experience and edge cases

**Changes**:
- Browser back/forward button support
- Preserve scroll position when switching tabs
- Loading states for cached vs fresh data
- Cache expiration (optional)

**Files Modified**:
- `static/js/app.js`: Enhanced navigation
- `static/js/clips.js`: UX improvements
- `templates/base.html`: CSS for loading states (if needed)

## Detailed Technical Specification

### Hash Values
```javascript
// URL hash to tab mapping
const HASH_TO_TAB = {
    '': 'home',           // http://localhost:5001/
    '#clips': 'clips',    // http://localhost:5001/#clips
    '#settings': 'settings' // http://localhost:5001/#settings
};
```

### Core Functions

#### `showTabFromHash()`
```javascript
function showTabFromHash() {
    const hash = window.location.hash;
    const tabName = HASH_TO_TAB[hash] || 'home';
    showTab(tabName);
}
```

#### `setTabHash(tabName)`
```javascript
function setTabHash(tabName) {
    const hash = Object.keys(HASH_TO_TAB).find(
        key => HASH_TO_TAB[key] === tabName
    );
    if (hash !== undefined) {
        window.location.hash = hash;
    }
}
```

### Clips Caching Structure
```javascript
const clipsCache = {
    cloud: {
        data: null,
        timestamp: null,
        loading: false
    },
    local: {
        data: null,
        timestamp: null,
        loading: false
    }
};
```

### Event Flow
1. **Tab Click**: `showTab(name)` → `setTabHash(name)` → triggers `hashchange`
2. **Hash Change**: `hashchange` event → `showTabFromHash()` → `showTab(name)`
3. **Page Load**: `DOMContentLoaded` → `showTabFromHash()`
4. **Clips Load**: Check cache → Use cached data OR fetch from server

## Backward Compatibility
- Existing functionality remains unchanged
- No server-side modifications required
- Graceful degradation if JavaScript disabled

## Testing Strategy
- Test URL persistence across page reloads
- Verify cache behavior when switching tabs
- Test browser back/forward navigation
- Validate clips refresh functionality

## Success Criteria
1. ✅ URL shows current tab (`#clips`, `#settings`)
2. ✅ Page reload preserves active tab
3. ✅ Switching tabs doesn't reload clips from server
4. ✅ Explicit refresh button still works
5. ✅ Browser back/forward buttons work correctly

## Future Enhancements
- Deep linking to specific clips (`#clips/12345`)
- URL parameters for filters (`#clips?storage=local`)
- Cache expiration and refresh strategies
- Offline support with cached data
