# 🖼️ Frontend Integration: Deep Research Agent

## ⚠️ Important Update

The backend now returns **Rich Markdown with images** in research responses. Your Frontend must render these images correctly.

---

## 📝 Markdown Image Format

The backend sends images in standard Markdown format:

```markdown
![Image Alt Text](https://example.com/image.jpg)
```

**Example Response:**
```json
{
  "reply": "Here's the iPhone 15:\n\n![iPhone 15](https://example.com/iphone15.jpg)\n\nThe price is ₹79,900 on Amazon.",
  "intent": "deep_research"
}
```

---

## ✅ Frontend Requirements

### 1. Markdown Renderer with Image Support

You **must** use a Markdown renderer that supports images.

**React (Recommended):**
```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function MessageBubble({ content }) {
  return (
    <ReactMarkdown 
      remarkPlugins={[remarkGfm]}
      components={{
        img: ({node, ...props}) => (
          <img 
            {...props} 
            style={{
              maxWidth: '100%',
              borderRadius: '8px',
              margin: '10px 0'
            }}
            onError={(e) => {
              // Handle broken images gracefully
              e.target.style.display = 'none';
            }}
          />
        )
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

**Install:**
```bash
npm install react-markdown remark-gfm
```

**Vue:**
```vue
<template>
  <div v-html="renderedMarkdown"></div>
</template>

<script>
import { marked } from 'marked';

export default {
  props: ['content'],
  computed: {
    renderedMarkdown() {
      return marked(this.content);
    }
  }
}
</script>
```

**Angular:**
```typescript
import { MarkdownModule } from 'ngx-markdown';

// In your component
@Component({
  template: '<markdown [data]="content"></markdown>'
})
```

---

## 🎨 Styling Recommendations

### Image Styling
```css
/* In your chat message component */
.message-content img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 10px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Responsive images */
@media (max-width: 768px) {
  .message-content img {
    max-width: 100%;
  }
}
```

### Error Handling
```tsx
// Handle broken image URLs
<img 
  src={imageUrl}
  alt={altText}
  onError={(e) => {
    e.target.style.display = 'none';
    // Optionally show placeholder
    // e.target.src = '/placeholder-image.png';
  }}
/>
```

---

## 🧪 Testing Checklist

Before deploying, test:

- [ ] Images render correctly in chat messages
- [ ] Images are responsive (mobile-friendly)
- [ ] Broken image URLs are handled gracefully
- [ ] Images don't break chat layout
- [ ] Images load asynchronously (don't block UI)
- [ ] Image URLs are absolute (not relative)

---

## 📊 Example Test Cases

### Test 1: E-Commerce Research
**Query:** "Find the best price for iPhone 15 on Amazon vs Flipkart"

**Expected:** Response should include:
- Product image (iPhone 15)
- Price information
- Source URLs

**Verify:** Image displays correctly in chat UI

### Test 2: Travel Research
**Query:** "Check Garuda bus availability from Hyderabad to Nirmal"

**Expected:** Response may include:
- Bus company logo/image
- Route information
- Source URLs

**Verify:** Any images render correctly

### Test 3: News Research
**Query:** "What is the latest update on the Stock Market today?"

**Expected:** Response may include:
- News website logo
- Chart images (if available)
- Source URLs

**Verify:** Images don't break layout

---

## 🔍 Debugging

### Issue: Images Not Displaying

**Check:**
1. Is Markdown renderer configured for images?
2. Are image URLs absolute (starting with `http://` or `https://`)?
3. Check browser console for CORS errors
4. Verify image URLs are accessible

**Common Causes:**
- Markdown renderer doesn't support images
- Image URLs are relative (should be absolute)
- CORS blocking (some sites block hotlinking)
- Broken image URLs (handle with `onError`)

### Issue: Images Break Layout

**Fix:**
```css
.message-content img {
  max-width: 100%;
  height: auto;
  display: block;
}
```

---

## 📚 Resources

- [react-markdown Documentation](https://github.com/remarkjs/react-markdown)
- [Markdown Image Syntax](https://www.markdownguide.org/basic-syntax/#images)
- [Handling Broken Images](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#handling_image_loading_errors)

---

## ✅ Integration Complete

Once images render correctly, the Deep Research Agent is fully integrated! 🎉

**Next Steps:**
- Test with real research queries
- Monitor image loading performance
- Handle edge cases (broken URLs, CORS, etc.)

---

**Questions?** Contact the Backend team or refer to `DEPLOYMENT_STRATEGY.md`

