# SUITS‑19: React Basics
 
**Researched by:** Kenny
**For:** Kenny and Vlad
**Leads to:** SUITS‑12 (HUD shows live O2)
 
---
 
## What React is
 
React is a JavaScript library for building web pages that update themselves.
 
Think of it like a scoreboard. You don't redraw the screen by hand. You change a value, and React updates the screen for you.
 
---
 
## How it works
 
1. React draws the page
2. The page connects to a data source
3. New data comes in
4. We save the new value
5. React sees the change and redraws
This repeats every time new data arrives.
 
---
 
## How it fits our project
 
```
TSS  →  Vlad's Python bridge  →  Kenny's React HUD
```
 
- The TSS sends telemetry, but browsers can't read it directly
- Vlad's bridge reads the TSS and passes the data to the HUD over a WebSocket (a connection that stays open)
- The React HUD receives each update and shows it on screen, like live O2
---
 
## Key words
 
- **Component:** a function that draws one part of the screen (like an O2 box)
- **State:** a value React remembers; changing it updates the screen
- **Props:** values a parent component passes down to a child, like function arguments (read only)
- **Effect:** code that runs after the page draws; this is where we connect to the bridge
- **Cleanup:** code that closes the connection so we never open two by accident
---
 
## Spike questions
 
**1. How do we start?**
With a tool called Vite. The app will live in a `hud/` folder in our repo.
 
**2. What are components, props, and state?**
Components draw the screen. Props are values passed into them. State is what changes.
 
**3. How does the page update itself?**
When new data arrives, we save it as state, and React redraws.
 
**4. How do we avoid duplicate connections?**
Connect once, and always close the connection in cleanup.
 
**5. JavaScript or TypeScript?**
Not decided. We'll pick together.
 
---
 
## Next
 
- **Kenny:** build SUITS‑12
- **Vlad:** build the bridge WebSocket (SUITS‑22)
- **Both:** agree on the JSON field names (SUITS‑20) and pick JS or TS
 