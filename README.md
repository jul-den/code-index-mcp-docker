# Code Index MCP – Docker‑ready fork

<div align="center">

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://www.docker.com/)

**Intelligent code indexing and analysis for Large Language Models**  
*– now with seamless Docker deployment –*

</div>

> **📦 This is a Docker‑focused fork** of the excellent [code-index-mcp](https://github.com/johnhuang316/code-index-mcp) by [johnhuang316](https://github.com/johnhuang316).  
> **⚠️ Important:** The issue that required this fork was fixed by the author in version `2.17.0`.  
> This fork is now **only for convenience** – it provides a pre‑built image for fast Docker startup without building from source.  
> If you want the latest features and fixes, please use the [original project](https://github.com/johnhuang316/code-index-mcp) (supports `pip`/`uvx` and also runs in Docker with the official `Dockerfile`).  
> **No original functionality is changed** – the server works exactly the same as upstream.
---

## Overview

Code Index MCP is a [Model Context Protocol](https://modelcontextprotocol.io) server that bridges the gap between AI models and complex codebases. It provides intelligent indexing, advanced search capabilities, and detailed code analysis to help AI assistants understand and navigate your projects effectively.

**Perfect for:** Code review, refactoring, documentation generation, debugging assistance, and architectural analysis.

This fork makes it easy to run the Code Index MCP server inside a container, with HTTP transports and support for `stdio` via `docker exec`.

### Why this fork? (now only for pre‑built image convenience)

> The original issue with Docker (in versions before 2.17.0) has been fixed upstream.  
> This fork remains useful **only if** you want to skip building from source and use a ready‑to‑run image.

- **Pre‑built image** on GitHub Container Registry – just `docker-compose up`
- **No need to clone or build** – ideal for quick testing or deployment
- **All environment variables (`MCP_*`)** supported, same as upstream
- **`docker-compose.yml` examples** for `streamable-http`, `sse`, and `stdio` (via `sleep infinity`)
- The core logic is **unchanged** – it’s the same as upstream `2.17.0` (the fix is included)

If you prefer to build your own image or run without Docker, use the [original project](https://github.com/johnhuang316/code-index-mcp) directly.


## Quick Start: use pre-built image (recommended for most users)

> ✅ **This is the main reason this fork exists today** – you get a pre‑built image without building from source.  
> The original Docker issue is already fixed in version `2.17.0`, so you are not missing any fixes by using this image.

1. **Create `docker-compose.yml`** with the content below, or download from the repository and save in an empty directory.
2. **Adjust volumes** – mount your code folder and a persistent directory for indexes.
3. **Run**:
   Make sure you are in the directory containing `docker-compose.yml`
   ```bash
   docker-compose up -d
   ```

<details>
<summary>📄 Minimal `docker-compose.yml` (click to expand)</summary>

```yaml
services:
  code-index-mcp-docker:
    image: ghcr.io/jul-den/code-index-mcp-docker:latest
    container_name: code-index-mcp-docker
    ports:
      - "8000:8000"
    volumes:
      - ./codefolder:/monitorfolder:ro
      - ./index_data:/data/index
    environment:
      - PYTHONUNBUFFERED=1
      - MCP_TRANSPORT=streamable-http
      - MCP_MOUNT_PATH=/mcp
      - MCP_INDEXER_PATH=/data/index
      - MCP_PROJECT_PATH=/monitorfolder
    restart: unless-stopped
```

</details>

> **One-liner without Compose:**
> ```bash
> docker run -d --name code-index-mcp -p 8000:8000 -v ./codefolder:/monitorfolder:ro -v ./index_data:/data/index -e MCP_TRANSPORT=streamable-http -e MCP_MOUNT_PATH=/mcp -e MCP_INDEXER_PATH=/data/index -e MCP_PROJECT_PATH=/monitorfolder -e PYTHONUNBUFFERED=1 ghcr.io/jul-den/code-index-mcp-docker:latest
> ```

Then configure your MCP client as shown in the example below.

## Manual build (from source)

> **Note:** Building from source is **not necessary** for most users – use the pre‑built image above.  
> This section is provided for completeness, but the resulting image will be identical to running upstream’s own `Dockerfile` (they have incorporated the fix as of version 2.17.0).
> 
### 1. Clone and run

```bash
git clone https://github.com/jul-den/code-index-mcp-docker.git
cd code-index-mcp-docker
```

### 2. Run with HTTP transport (recommended for network access)

Use `streamable-http` (or `sse`) when your MCP client supports HTTP endpoints (e.g., LM Studio, Claude Desktop with network support).

**Create `docker-compose.build.yml`** with the content below, or download from the repository and save in an empty directory.

<details>
<summary>📄 Minimal `docker-compose.build.yml` (click to expand)</summary>

```yaml
services:
  code-index-mcp-docker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: code-index-mcp-docker
    ports:
      - "8000:8000"
    volumes:
      - ./codefolder:/monitorfolder:ro
      - ./index_data:/data/index
    environment:
      - PYTHONUNBUFFERED=1
      - MCP_PROJECT_PATH=/monitorfolder
      - MCP_TRANSPORT=streamable-http
      - MCP_MOUNT_PATH=/mcp
      - MCP_INDEXER_PATH=/data/index
      # - MCP_TOOL_PREFIX="docker:"
    restart: unless-stopped
```
</details>
  
Start the container:
Make sure you are in the directory containing `docker-compose.build.yml`

```bash
docker-compose -f docker-compose.build.yml up -d
```

Then configure your MCP client as shown in the example below.


## Example MCP client configuration (e.g., `mcp.json`)

In your MCP client, set the URL to:

- `http://127.0.0.1:8000/mcp` (for `streamable-http`)
- `http://127.0.0.1:8000/mcp/sse` (for `sse`)


```json
{
  "mcpServers": {
    "code-index-mcp-docker": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
      },
      "timeout": 30000
    }
  }
}
```

## `stdio` transport (alternative, not recommended for Docker)

> **⚠️ Note:** For Docker deployments, HTTP transports (`streamable-http` or `sse`) are **strongly recommended**.  
> Using `stdio` via `docker exec` adds per‑call overhead (startup latency).  
> Only use this method if your MCP client does **not** support HTTP endpoints.

**If you still need `stdio`**, follow these steps:

  1. **Create `docker-compose.stdio.yml`** with the content below, or download from the repository and save in an empty directory.

  2. **Start a persistent idle container** (keeps the container alive):
```bash
docker-compose -f docker-compose.stdio.yml up -d
```

Where `docker-compose.stdio.yml` contains:
```yaml
services:
  code-index-mcp-docker-stdio:
    image: ghcr.io/jul-den/code-index-mcp-docker:latest
    container_name: code-index-mcp-docker-stdio
    volumes:
      - ./codefolder:/monitorfolder:ro
      - ./index_data:/data/index
    entrypoint: ["/bin/sh", "-c"]
    command: ["sleep infinity"]
    environment: PYTHONUNBUFFERED=1
    restart: unless-stopped
```
  
  3. **Configure your MCP client** (e.g., `mcp.json`):
    ```json
    {
     "mcpServers": {
       "code-index-mcp-docker-stdio": {
         "command": "docker",
         "args": [
           "exec", "-i", "code-index-mcp-docker-stdio",
           "python", "/app/run.py",
           "--transport", "stdio",
           "--project-path", "/monitorfolder",
           "--indexer-path", "/data/index",
           "--tool-prefix", "io:"
         ]
       }
     }
    }
    ```

> The container stays alive (`sleep infinity`); each MCP call launches a fresh `run.py` process via `docker exec`.  
> For one‑shot containers (slower, not recommended), use `docker run --rm ...` instead of `docker exec`.


## Environment variables vs. command line arguments

The entrypoint `run.py` accepts both:
- **Environment variables** (prefixed with `MCP_`) – convenient for `docker-compose.yml`.
- **Direct command line arguments** – as shown in the `stdio` example.

| Variable               | CLI argument          | Description                                      |
|------------------------|-----------------------|--------------------------------------------------|
| `MCP_PROJECT_PATH`     | `--project-path`      | Path to the project to index (inside container)  |
| `MCP_TRANSPORT`        | `--transport`         | `streamable-http`, `sse`, or `stdio`             |
| `MCP_PORT`             | `--port`              | Port for HTTP transports                         |
| `MCP_MOUNT_PATH`       | `--mount-path`        | URL prefix for SSE/HTTP                          |
| `MCP_INDEXER_PATH`     | `--indexer-path`      | Custom index storage directory                   |
| `MCP_TOOL_PREFIX`      | `--tool-prefix`       | Prefix for tool names                            |

## Viewing logs

All logs (INFO and above) are sent to `stdout` inside the container. View them with:

```bash
docker logs code-index-mcp-docker
docker logs code-index-mcp-docker-stdio
```

---

## Typical Use Cases

**Code Review**: "Find all places using the old API"  
**Refactoring Help**: "Where is this function called?"  
**Learning Projects**: "Show me the main components of this React project"  
**Debugging**: "Search for all error handling related code"

## Key Features

### 🔍 **Intelligent Search & Analysis**
- **Dual-Strategy Architecture**: Specialized tree-sitter parsing for 10 core languages, fallback strategy for 50+ file types
- **Direct Tree-sitter Integration**: No regex fallbacks for specialized languages - fail fast with clear errors
- **Advanced Search**: Auto-detects and uses the best available tool (ugrep, ripgrep, ag, or grep)
- **Universal File Support**: Comprehensive coverage from advanced AST parsing to basic file indexing
- **File Analysis**: Deep insights into structure, imports, classes, methods, and complexity metrics after running `build_deep_index`

### 🗂️ **Multi-Language Support**  
- **10 Languages with Tree-sitter AST Parsing**: Python, JavaScript, TypeScript, Java, Kotlin, C#, Go, Objective-C, Zig, Rust
- **50+ File Types with Fallback Strategy**: C/C++, Ruby, PHP, and all other programming languages
- **Document & Config Files**: Markdown, JSON, YAML, XML with appropriate handling
- **Web Frontend**: Vue, React, Svelte, HTML, CSS, SCSS
- **Java Web & Build**: JSP/Tag files (`.jsp`, `.jspx`, `.jspf`, `.tag`, `.tagx`), Grails/GSP (`.gsp`), Gradle & Groovy builds (`.gradle`, `.groovy`), `.properties`, and Protocol Buffers (`.proto`)
- **Database**: SQL variants, NoSQL, stored procedures, migrations
- **Configuration**: JSON, YAML, XML, Markdown
- **[View complete list](#supported-file-types)**

### ⚡ **Real-time Monitoring & Auto-refresh**
- **File Watcher**: Automatic index updates when files change
- **Cross-platform**: Native OS file system monitoring
- **Smart Processing**: Batches rapid changes to prevent excessive rebuilds
- **Shallow Index Refresh**: Watches file changes and keeps the file list current; run a deep rebuild when you need symbol metadata

### ⚡ **Performance & Efficiency**
- **Tree-sitter AST Parsing**: Native syntax parsing for accurate symbol extraction
- **Persistent Caching**: Stores indexes for lightning-fast subsequent access
- **Smart Filtering**: Intelligent exclusion of build directories and temporary files
- **Memory Efficient**: Optimized for large codebases
- **Direct Dependencies**: No fallback mechanisms - fail fast with clear error messages

## Supported File Types

<details>
<summary><strong>📁 Programming Languages (Click to expand)</strong></summary>

**Languages with Specialized Tree-sitter Strategies:**
- **Python** (`.py`, `.pyw`) - Full AST analysis with class/method extraction and call tracking
- **JavaScript** (`.js`, `.jsx`, `.mjs`, `.cjs`) - ES6+ class and function parsing with tree-sitter
- **TypeScript** (`.ts`, `.tsx`) - Complete type-aware symbol extraction with interfaces
- **Java** (`.java`) - Full class hierarchy, method signatures, and call relationships
- **Kotlin** (`.kt`, `.kts`) - Package-aware symbol extraction with methods and call relationships
- **C#** (`.cs`) - Namespace-aware type/member extraction with call relationships
- **Go** (`.go`) - Struct methods, receiver types, and function analysis
- **Rust** (`.rs`) - Functions, module-aware names, impl methods, structs/enums/traits, and basic call relationships
- **Objective-C** (`.m`, `.mm`) - Class/instance method distinction with +/- notation
- **Zig** (`.zig`, `.zon`) - Function and struct parsing with tree-sitter AST

**All Other Programming Languages:**
All other programming languages use the **FallbackParsingStrategy** which provides basic file indexing and metadata extraction. This includes:
- **System & Low-Level:** C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)
- **Object-Oriented:** Scala (`.scala`), Swift (`.swift`)
- **Scripting & Dynamic:** Ruby (`.rb`), PHP (`.php`), Shell (`.sh`, `.bash`)
- **And 40+ more file types** - All handled through the fallback strategy for basic indexing

</details>

<details>
<summary><strong>🌐 Web & Frontend (Click to expand)</strong></summary>

**Frameworks & Libraries:**
- Vue (`.vue`)
- Svelte (`.svelte`)
- Astro (`.astro`)

**Styling:**
- CSS (`.css`, `.scss`, `.less`, `.sass`, `.stylus`, `.styl`)
- HTML (`.html`)

**Templates:**
- Handlebars (`.hbs`, `.handlebars`)
- EJS (`.ejs`)
- Pug (`.pug`)
- FreeMarker (`.ftl`)
- Mustache (`.mustache`)
- Liquid (`.liquid`)
- ERB (`.erb`)

</details>

<details>
<summary><strong>🗄️ Database & SQL (Click to expand)</strong></summary>

**SQL Variants:**
- Standard SQL (`.sql`, `.ddl`, `.dml`)
- Database-specific (`.mysql`, `.postgresql`, `.psql`, `.sqlite`, `.mssql`, `.oracle`, `.ora`, `.db2`)

**Database Objects:**
- Procedures & Functions (`.proc`, `.procedure`, `.func`, `.function`)
- Views & Triggers (`.view`, `.trigger`, `.index`)

**Migration & Tools:**
- Migration files (`.migration`, `.seed`, `.fixture`, `.schema`)
- Tool-specific (`.liquibase`, `.flyway`)

**NoSQL & Modern:**
- Graph & Query (`.cql`, `.cypher`, `.sparql`, `.gql`)

</details>

<details>
<summary><strong>📄 Documentation & Config (Click to expand)</strong></summary>

- Markdown (`.md`, `.mdx`)
- Configuration (`.json`, `.xml`, `.yml`, `.yaml`, `.properties`)

</details>


## Available Tools

### 🏗️ **Project Management**
| Tool | Description |
|------|-------------|
| **`set_project_path`** | Initialize indexing for a project directory |
| **`refresh_index`** | Rebuild the shallow file index after file changes |
| **`build_deep_index`** | Generate the full symbol index used by deep analysis |
| **`get_settings_info`** | View current project configuration and status |

*Run `build_deep_index` when you need symbol-level data; the default shallow index powers quick file discovery.*

### 🔍 **Search & Discovery**
| Tool | Description |
|------|-------------|
| **`search_code_advanced`** | Smart search with literal-by-default matching, optional `regex=True`, fuzzy matching, file filtering, and paginated results (10 per page by default); regex mode requires a native search tool because the basic fallback is literal-only |
| **`find_files`** | Locate files using glob patterns (e.g., `**/*.py`) |
| **`get_file_summary`** | Analyze file structure, functions, imports, and complexity (requires deep index) |

### 🔄 **Monitoring & Auto-refresh**
| Tool | Description |
|------|-------------|
| **`get_file_watcher_status`** | Check file watcher status and configuration |
| **`configure_file_watcher`** | Enable/disable auto-refresh and configure settings |

### 🛠️ **System & Maintenance**
| Tool | Description |
|------|-------------|
| **`create_temp_directory`** | Set up storage directory for index data |
| **`check_temp_directory`** | Verify index storage location and permissions |
| **`clear_settings`** | Reset all cached data and configurations |
| **`refresh_search_tools`** | Re-detect available search tools (ugrep, ripgrep, etc.) |

## Usage Examples

### 🎯 **Quick Start Workflow**

**1. Initialize Your Project**
```
Set the project path to /Users/dev/my-react-app
```
*Automatically indexes your codebase and creates searchable cache*

**2. Explore Project Structure**
```
Find all TypeScript component files in src/components
```
*Uses: `find_files` with pattern `src/components/**/*.tsx`*

**3. Analyze Key Files**
```
Give me a summary of src/api/userService.ts
```
*Uses: `get_file_summary` to show functions, imports, and complexity*
*Tip: run `build_deep_index` first if you get a `needs_deep_index` response.*

### 🔍 **Advanced Search Examples**

<details>
<summary><strong>Code Pattern Search</strong></summary>

```
Search for all function calls matching "get.*Data" using `regex=True`
```
*Finds: `getData()`, `getUserData()`, `getFormData()`, etc. Regex search is opt-in; install a native search tool and use `regex=True` because the basic fallback stays literal-only.*

</details>

<details>
<summary><strong>Fuzzy Function Search</strong></summary>

```
Find authentication-related functions with fuzzy search for 'authUser'
```
*Matches: `authenticateUser`, `authUserToken`, `userAuthCheck`, etc.*

</details>

<details>
<summary><strong>Language-Specific Search</strong></summary>

```
Search for "API_ENDPOINT" only in Python files
```
*Uses: `search_code_advanced` with literal matching and `file_pattern: "*.py"` (defaults to 10 matches; use `max_results` to expand or `start_index` to page)*

</details>

<details>
<summary><strong>Auto-refresh Configuration</strong></summary>

```
Configure automatic index updates when files change
```
*Uses: `configure_file_watcher` to enable/disable monitoring and set debounce timing*

</details>

<details>
<summary><strong>Project Maintenance</strong></summary>

```
I added new components, please refresh the project index
```
*Uses: `refresh_index` to update the searchable cache*

</details>

## Troubleshooting

### 🔄 **Auto-refresh Not Working**

If automatic index updates aren't working when files change, try:
- `pip install watchdog` (may resolve environment isolation issues)
- Use manual refresh: Call the `refresh_index` tool after making file changes
- Check file watcher status: Use `get_file_watcher_status` to verify monitoring is active

### **macOS File Watcher Options**

The default FSEvents observer works well for most projects. If you experience issues, you can switch to an alternative observer via `configure_file_watcher`:

- `"auto"` (default): Platform default (FSEvents on macOS)
- `"kqueue"`: Kqueue observer (macOS/BSD)
- `"fsevents"`: Force FSEvents (macOS only)
- `"polling"`: Cross-platform polling fallback

Note: Kqueue opens one file descriptor per watched file. For large projects using kqueue, you may need to increase the limit: `ulimit -n 10240`

---

## License & Attribution

This project is a **fork** of [code-index-mcp](https://github.com/johnhuang316/code-index-mcp) by **johnhuang316** and is released under the same **MIT License**.  
All original copyright and license notices apply. The Docker‑related additions ( `run.py`, `docker-compose.yml`) are also provided under the MIT License.

**Maintainer of this fork:** [jul-den](https://github.com/jul-den)  
**Upstream project:** [johnhuang316/code-index-mcp](https://github.com/johnhuang316/code-index-mcp)

**Status of this fork:** The original Docker issue was fixed upstream in `v2.17.0`.  
This fork now exists **only** to provide a pre‑built image for faster startup.  
For the latest code and official support, use the upstream repository.

If you find this fork useful, please consider giving a ⭐ to the **original repository** – the author did the hard work!

---

## Contributing to the fork

If you want to improve the Docker experience, feel free to open issues or pull requests in this fork.  
For changes to the core MCP functionality, please contribute directly to the [upstream project](https://github.com/johnhuang316/code-index-mcp).
