# Dependency Resolver UI

Beautiful, responsive React-based UI for the Dependency Resolver Agent, inspired by Claude's assistant interface.

## 🎨 Design Features

### Theme System
- **Light Theme** (Default) - Clean, professional look
- **Dark Theme** - Eye-friendly for long sessions
- **Primary Color** - #009eda (Claude blue)
- **Dynamic Switching** - Toggle button in header

### Responsive Layout
- Desktop: 3-column layout (input, results, sidebar)
- Tablet: 2-column layout
- Mobile: Single column, vertical scroll

### Interactive Elements
- Tab-based navigation (Input, Results, History)
- Real-time status indicators
- Quick template insertion
- Copy-friendly code displays

## 🚀 Getting Started

### Option 1: Direct Browser (Recommended)

1. **Open the file directly in browser**:
   ```bash
   # Navigate to the file
   open frontend/index.html
   # or
   firefox frontend/index.html
   ```

2. **Visit with query parameters**:
   - Light theme: `file:///path/to/index.html`
   - Dark theme: `file:///path/to/index.html?theme=dark`

### Option 2: Local HTTP Server

```bash
# Using Python 3
python3 -m http.server 3000 --directory frontend

# Using Python 2
python -m SimpleHTTPServer 3000

# Using Node (http-server)
npx http-server frontend -p 3000

# Using Ruby
ruby -run -ehttpd frontend -p 3000
```

Then visit: `http://localhost:3000`

### Option 3: Docker

```bash
docker run -p 8080:80 -v $(pwd)/frontend:/usr/share/nginx/html nginx:latest
```

Then visit: `http://localhost:8080`

## 🎯 URL Parameters

Control theme via URL query parameters:

```
http://localhost:3000?theme=light
http://localhost:3000?theme=dark
```

The UI remembers your choice in localStorage for future visits.

## 🧩 UI Components

### Header
- App title with logo
- Theme toggle button (Sun/Moon icon)
- Responsive navigation

### Main Content
- **Input Tab**: File type selector, template insertion, content textarea
- **Results Tab**: Resolved dependencies, conflicts, validation status
- **History Tab**: Session ID, iteration count, package stats

### Sidebar
- Status panel (theme, API status)
- Features list
- Help section
- Theme control info

### Templates

Quick templates for both file types:

**package.json**:
```json
{
  "dependencies": {
    "express": "^4.0.0",
    "lodash": "^4.17.0"
  }
}
```

**requirements.txt**:
```
django>=3.0,<4.0
celery==5.1.2
redis>=3.0
```

## 🔌 API Integration

The UI connects to the backend API:

```javascript
POST http://localhost:8000/dependency-resolver/resolve
```

**Request**:
```json
{
  "file_type": "package.json",
  "content": "{\"dependencies\": {...}}",
  "auto_resolve": true,
  "session_id": null
}
```

**Response**:
```json
{
  "status": "DONE",
  "resolved_dependencies": {...},
  "dependency_graph": {...},
  "conflicts": [],
  "validation": {...},
  "session_id": "abc-123"
}
```

## 🎨 Theme Customization

To change the primary color, edit the CSS variables in the style block:

```css
:root {
    --primary-color: #009eda;      /* Main color */
    --primary-light: #e8f7fd;      /* Light variant */
    --primary-dark: #006fa8;       /* Dark variant */
}
```

## 📱 Responsive Breakpoints

- **Mobile**: < 768px (1 column)
- **Tablet**: 768px - 1024px (2 columns)
- **Desktop**: > 1024px (3 columns)

## ⚙️ Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 📦 Dependencies

All loaded from CDN:
- React 18
- ReactDOM 18
- Babel Standalone
- Tailwind CSS
- Lucide Icons (SVG)

No build step required! Pure HTML/JS.

## 🔒 Security

- CORS-enabled for API calls
- No local storage of sensitive data
- XSS protection via React escaping
- Input validation before API calls

## 🐛 Troubleshooting

### API Connection Failed
**Issue**: "Failed to resolve dependencies"

**Solution**: 
1. Ensure backend is running: `uvicorn main:app --reload`
2. Check CORS is enabled in backend
3. Verify API endpoint: `http://localhost:8000`

### Theme Not Changing
**Solution**:
1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. Clear localStorage: `localStorage.clear()`
3. Try URL parameter: `?theme=dark`

### Tailwind Styles Not Loading
**Solution**:
1. Check internet connection (CDN)
2. Try offline version (build with webpack/parcel)
3. Use local Tailwind CSS

## 📈 Performance

- **Initial Load**: ~200ms (with CDN)
- **API Call**: 1-5s depending on complexity
- **Theme Switch**: <50ms

## 🎓 Code Structure

```javascript
// Main App Component
function DependencyResolverUI() {
  // Theme state
  const [theme, setTheme] = useState(getTheme());
  
  // Form state
  const [fileType, setFileType] = useState('package.json');
  const [content, setContent] = useState('');
  
  // Result state
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Handle resolve
  const handleResolve = async () => { ... }
  
  // Render UI
  return (...)
}
```

## 🚀 Deployment Options

### Option 1: Static Hosting (GitHub Pages)
```bash
cp frontend/index.html docs/index.html
git push origin main
# Access at: https://username.github.io/repo
```

### Option 2: Netlify
```bash
# Just drag frontend/index.html to netlify.com
# Or use CLI:
npm install -g netlify-cli
netlify deploy --dir=frontend
```

### Option 3: Vercel
```bash
npx vercel --prod --name dependency-resolver
```

### Option 4: Docker + Backend
```dockerfile
FROM nginx:latest
COPY frontend /usr/share/nginx/html
EXPOSE 80
```

## 📚 Related Files

- `backend/README.md` - Backend setup
- `QUICKSTART.md` - Project quickstart
- `COMPLETE_SYSTEM.md` - Full system overview

## 🤝 Contributing

The UI is self-contained in a single HTML file. To modify:

1. Edit CSS in the `<style>` block
2. Edit React component in the `<script type="text/babel">` block
3. No build process needed - refresh browser

## 📄 License

Same as the main project.

## 🎉 Features

✅ Light/Dark theme toggle  
✅ Responsive design  
✅ Real-time API integration  
✅ Multiple tabs (Input, Results, History)  
✅ Quick templates  
✅ Status indicators  
✅ Error messages  
✅ Session tracking  
✅ Theme persistence  
✅ Mobile-friendly  

---

**Enjoy resolving dependencies with style!** 🎨✨
