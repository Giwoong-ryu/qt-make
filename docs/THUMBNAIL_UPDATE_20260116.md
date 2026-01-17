# Session Update: Thumbnail System Enhancement (2026-01-16)

## Session Context
- **Date**: 2026-01-16
- **Scope**: Thumbnail generation system overhaul, drag-and-drop editor implementation
- **Status**: Core implementation complete, integration pending for some features

---

## Files Modified

### Backend

#### `backend/app/main.py`
- **Line 13**: Added `from pydantic import BaseModel`
- **Lines 942-1072**: Added `TextBoxPosition(BaseModel)` and `QTThumbnailRequest(BaseModel)` classes
- **Lines 963-1072**: Added `POST /api/thumbnail/generate-qt` endpoint for custom position thumbnail generation
  - Accepts `text_boxes[]` with x/y percentages, fontSize, fontFamily, color
  - Downloads background image via httpx
  - Generates thumbnail using FFmpeg drawtext filters
  - Returns base64-encoded JPEG

#### `backend/app/services/thumbnail.py`
- **Lines 331-340**: Updated `generate_qt_thumbnail()` signature to add `layout: str = "classic"` parameter
- **Lines 380-412**: Added `layouts` dictionary with 4 presets:
  - `classic`: Top-center titles, bottom-right verse
  - `minimal`: All text centered
  - `modern`: Left-aligned top, bottom-right verse
  - `prayer`: Large centered title, bottom-center verse
- **Lines 423-483**: Refactored text rendering to use `layout_cfg` for dynamic positions

#### `backend/app/services/video.py`
- **Lines 87-135**: Added `compose_video_with_thumbnail()` method
- **Lines 137-190**: Added `_add_thumbnail_intro()` method
  - Uses FFmpeg xfade filter for fade transition
  - Default: 2 seconds display + 1 second fade

### Frontend

#### `frontend/src/components/ThumbnailEditor.tsx` (NEW)
- Canvas-based drag-and-drop editor
- 4 draggable text boxes: main, sub, date, verse
- Mouse drag handlers: `handleMouseDown`, `handleMouseMove`, `handleMouseUp`
- Control panel: font family select, fontSize slider (12-96), color picker
- State: `textBoxes: TextBox[]`, `selectedBox: string | null`, `isDragging: boolean`
- Props interface: `ThumbnailEditorProps` with callbacks `onSave`, `onGenerate`

#### `frontend/src/components/ThumbnailSettings.tsx` (NEW)
- Bible verse input form with 66 books dropdown (`BIBLE_BOOKS` array)
- Fields: mainTitle, subTitle, date, bibleBook, chapterStart, verseStart, verseEnd
- Auto-generates date on mount
- Collapsible accordion UI

#### `frontend/src/components/ThumbnailConceptPicker.tsx`
- Refactored for lazy loading
- Templates load only when category is expanded (accordion style)
- Added `lastUsedTemplateId` prop support
- State: `expandedCategory`, `templatesByCategory: Record<string, ThumbnailTemplate[]>`
- Uses `loading="lazy"` attribute on images

#### `frontend/src/components/VideoEditModal.tsx`
- **Line 28**: Added `import ThumbnailEditor from "./ThumbnailEditor"`
- **Line 53**: Added `thumbnailMode` state (`"editor" | "concept"`)
- **Lines 503-572**: Replaced thumbnail tab with mode toggle UI
  - "🎨 드래그 에디터" mode: Shows ThumbnailEditor
  - "🖼️ 컨셉 선택" mode: Shows ThumbnailConceptPicker

#### `frontend/src/components/index.ts`
- Added exports:
  - `ThumbnailSettingsForm`, `ThumbnailSettings` (type)
  - `ThumbnailEditor`, `ThumbnailLayout` (type)

---

## API Endpoints

### `POST /api/thumbnail/generate-qt`
Request body:
```json
{
  "background_image_url": "string",
  "text_boxes": [
    {
      "id": "main|sub|date|verse",
      "text": "string",
      "x": 0-100,
      "y": 0-100,
      "fontSize": 12-96,
      "fontFamily": "string",
      "color": "#FFFFFF",
      "visible": true
    }
  ],
  "overlay_opacity": 0.3,
  "output_width": 1920,
  "output_height": 1080
}
```
Response:
```json
{
  "thumbnail_base64": "data:image/jpeg;base64,...",
  "width": 1920,
  "height": 1080
}
```

---

## Type Definitions

### TextBox (Frontend)
```typescript
interface TextBox {
  id: string;
  label: string;
  text: string;
  x: number;      // 0-100 percent
  y: number;      // 0-100 percent
  fontSize: number;
  fontFamily: string;
  color: string;
  visible: boolean;
}
```

### ThumbnailLayout (Frontend)
```typescript
interface ThumbnailLayout {
  textBoxes: TextBox[];
  backgroundImageUrl?: string;
}
```

---

## Pending Implementation

1. **Layout persistence**: Save/load `ThumbnailLayout` per church via API
2. **YouTube thumbnail**: Separate 1280x720 generation and download
3. **BGM selection UI**: Integrate `BGMSelector` into upload form
4. **onGenerate callback**: Wire ThumbnailEditor to call `/api/thumbnail/generate-qt`

---

## Dependencies Added
- `from pydantic import BaseModel` in `backend/app/main.py`

## No Breaking Changes
- All existing APIs remain functional
- `generate_qt_thumbnail()` defaults to `layout="classic"` for backward compatibility
