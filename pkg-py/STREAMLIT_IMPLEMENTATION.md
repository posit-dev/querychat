# Streamlit Implementation Summary

## Overview
Added opt-in Streamlit support to the Python package via a `.streamlit_app()` method, providing an alternative to the existing Shiny `.app()` method.

## Current Implementation

### Core Method: `streamlit_app()`
Location: `pkg-py/src/querychat/_querychat.py:172-473`

Creates a complete Streamlit app with:
- Chat sidebar with scrollable history (height=500px container)
- Fixed chat input at bottom of sidebar
- Main content area with SQL display and data table
- Streaming LLM responses with inline tool results

### Key Features Implemented

#### 1. Streaming Support
- Uses `client.stream(prompt, echo="none", content="all")` to get both text and tool results
- Manual accumulation with `st.empty()` placeholder for `unsafe_allow_html=True`
- Displays streaming text with inline tool results (SQL queries + tables)
- Tool results show via `ContentToolResult.extra["display"].markdown`

#### 2. Tool Result Display
- `tool_query`: Shows SQL code block + formatted HTML table (first 5 rows)
- `tool_update_dashboard`: Shows SQL code block, updates session state
- Tool results render inline during streaming in correct order
- Historical messages also show tool results from `message["tool_results"]`

#### 3. Suggestion Buttons
- LLM wraps suggestions in `<span class="suggestion">text</span>`
- Extracted via regex and removed from display text
- Shown as `st.button(type="tertiary")` below messages
- Clicking stores in `querychat_pending_prompt` and triggers rerun
- Works for both streaming and historical messages
- No page reloads - pure Streamlit reactivity

#### 4. State Management
- `SessionStateReactive` helper class bridges Streamlit session state with tool API
- Wraps session state keys with `.get()` and `.set()` methods
- Tools registered once per session with this wrapper
- `querychat_pending_prompt` handles both chat input and suggestion clicks

### File Structure
```
pkg-py/
├── src/querychat/_querychat.py
│   └── QueryChatBase.streamlit_app()  # Main method
├── examples/
│   └── 04-streamlit-app.py            # Example usage
└── pyproject.toml                      # Added streamlit dependency group
```

### Dependencies
- Added `streamlit = ["streamlit>=1.28.0"]` to dependency groups
- Install with: `uv pip install --group streamlit`

## Usage Example

```python
from querychat import QueryChat
from seaborn import load_dataset

titanic = load_dataset("titanic")
qc = QueryChat(titanic, "titanic")
qc.streamlit_app()
```

Run with: `streamlit run app.py`

## Known Issues / TODO

### Current Behavior
- `.streamlit_app()` is a monolithic method that creates the entire app
- No way to use QueryChat in custom Streamlit apps (like Shiny's `.server()`)
- Can't access `df()`, `sql()`, `title()` reactively
- Can't integrate into existing Streamlit apps

### Needed for Custom Apps
To enable bespoke Streamlit apps, need an API similar to Shiny:

**Shiny Code Mode:**
```python
qc = QueryChat(data, "table")
vals = qc.server()  # Returns ServerValues
df = vals.df()      # Reactive calc
sql = vals.sql()    # Reactive value
```

**Desired Streamlit API:**
```python
qc = QueryChat(data, "table")
# Need: way to render chat UI and access reactive state
# qc.ui() - render chat interface
# qc.df() - access current dataframe
# qc.sql() - access current SQL
# qc.title() - access current title
```

**Challenge:** Streamlit has no true reactive system like Shiny. Session state + reruns are the pattern.

## Architecture Notes

### Shiny vs Streamlit Differences
1. **Reactivity**: Shiny has reactive graphs; Streamlit reruns entire script
2. **Modules**: Shiny has namespaced modules; Streamlit shares global scope
3. **UI/Server split**: Shiny separates clearly; Streamlit is more imperative
4. **Tool integration**: Shiny uses reactive values; Streamlit needs session state wrapper

### Design Decisions
- Chose session state wrapper over direct modification for consistency
- Used `st.container(height=500)` for scrollable chat with fixed input
- Extracted suggestions to buttons rather than links to avoid page reloads
- Store tool results in chat history for proper re-rendering

## Next Steps

### For Custom Streamlit Apps
Consider these approaches:

1. **Context Manager Pattern**
```python
with qc.chat_ui():
    # Renders chat interface, manages state
    pass

# Access state after
df = qc.df()
sql = qc.sql()
```

2. **Session State Integration**
```python
qc.setup()  # Initialize session state
qc.render_chat()  # Render UI
# Access via session state keys
df = st.session_state.querychat_df
```

3. **Separate UI and State**
```python
qc.render_sidebar()  # Just the chat UI
df = qc.get_df()  # Getter methods that read session state
sql = qc.get_sql()
```

4. **Express-style Pattern** (like existing `QueryChatExpress`)
```python
# Auto-initialization in constructor
qc = QueryChat(data, "table")
qc.sidebar()  # Renders and sets up state
df = qc.df()  # Property access
```

### Implementation Considerations
- Need to handle Streamlit's script rerun model
- Session state keys should be namespaced by `qc.id`
- Chat client needs to persist in session state
- Tool registration should happen once per session
- Greeting generation should be cached

## Files Modified
- `pkg-py/src/querychat/_querychat.py` - Added `streamlit_app()` method
- `pkg-py/examples/04-streamlit-app.py` - Example app
- `pyproject.toml` - Added streamlit dependency group
