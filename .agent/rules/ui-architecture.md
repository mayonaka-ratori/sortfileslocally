# UI Architecture Guidelines

Follow these patterns for Next.js/Tailwind development.

## Component Structure
- Use Functional Components with `export default function`.
- Adhere to "use client" or "use server" directives strictly.

### Example
```tsx
"use client"

import { useState } from "react"
import { Search } from "lucide-react"

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("")
  
  return (
    <div className="flex items-center gap-2 p-4 bg-zinc-900 rounded-lg">
      <Search className="w-5 h-5 text-zinc-400" />
      <input 
        value={query} 
        onChange={(e) => setQuery(e.target.value)}
        className="bg-transparent border-none outline-none text-white w-full"
      />
    </div>
  )
}
```

## Styling
- Use **Tailwind CSS 4** utility classes.
- Avoid inline styles or local CSS modules unless absolutely necessary for complex animations.
- Prefer `zinc` or `slate` palettes for dark mode consistency.

## Icons
- Exclusively use `lucide-react`.
