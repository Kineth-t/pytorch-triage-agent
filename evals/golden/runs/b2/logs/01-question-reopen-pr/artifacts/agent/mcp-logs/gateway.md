<details>
<summary>MCP Gateway</summary>

- ✓ **startup** MCPG Gateway version: v0.4.37
- ✓ **startup** Starting MCPG with config: stdin, listen: 0.0.0.0:8080, log-dir: /tmp/gh-aw/mcp-logs/
- ✓ **startup** WASM compilation cache directory: /tmp/gh-aw/wazero-cache
- ✓ **startup** Environment validation passed
- ✓ **startup** Loaded 2 MCP server(s): [github safeoutputs]
- ✓ **startup** Guards sink server ID logging enrichment disabled (no sink server IDs configured)
- ✓ **startup** OpenTelemetry tracing disabled (no OTLP endpoint configured)
- ✓ **backend**
  ```
  Successfully connected to MCP backend server, command=docker
  ```
- 🔍 rpc **safeoutputs**→`tools/list`
- 🔍 rpc **safeoutputs**←`resp` `{"jsonrpc":"2.0","id":1,"result":{"ttlMs":0,"cacheScope":"","tools":[{"description":"WRITE-ONCE: do NOT probe this tool with empty or placeholder arguments. If not ready to post a real comment, call noop. Adds a comment to an existing GitHub issue, pull request, or discussion; use create_issue, create_discussion, or create_pull_request for new items. IMPORTANT CONSTRAINTS: Input is limited to 524288 characters, 10 mentions, and configured max-links URL occurrences (default: 50). Oversized agent content is a...`
- ✓ **backend**
  ```
  Successfully connected to MCP backend server, command=docker
  ```
- 🔍 rpc **github**→`tools/list`
- 🔍 rpc **github**←`resp` `{"jsonrpc":"2.0","id":1,"result":{"ttlMs":0,"cacheScope":"","tools":[{"annotations":{"idempotentHint":false,"readOnlyHint":true,"title":"Get a specific label from a repository"},"description":"Get a specific label from a repository.","inputSchema":{"properties":{"name":{"description":"Label name.","type":"string"},"owner":{"description":"Repository owner (username or organization name)","type":"string","x-mcp-header":"owner"},"repo":{"description":"Repository name","type":"string","x-mcp-header":"repo"}},"r...`
- 🔍 rpc **github**→`prompts/list`
- 🔍 rpc **github**←`resp` `{"jsonrpc":"2.0","id":1,"result":{"ttlMs":0,"cacheScope":"","prompts":[{"arguments":[{"name":"repo","description":"The repository to assign tasks in (owner/repo).","required":true}],"description":"Assign GitHub Coding Agent to multiple tasks in a GitHub repository.","name":"AssignCodingAgent","icons":[{"src":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABmJLR0QA/wD/AP+gvaeTAAAC2UlEQVRIicWVMUyTaRjHf/+vVUpOJOdilOYoUvVreq2CDmLOwdlAS5xMbrrhBifjYG7QjYuJw108nZx1huLgYlw0QshxChUK2koxHHcuCmg...`
- ✓ **startup** Starting MCPG in ROUTED mode on 0.0.0.0:8080
- ✓ **startup** Routes: /mcp/<server> where <server> is one of: [github safeoutputs]
- ✓ **startup** TLS not configured — listening on http://0.0.0.0:8080 (set --tls-cert/--tls-key to enable)
- ✓ **backend**
  ```
  Successfully connected to MCP backend server, command=docker
  ```
- 🔍 rpc **safeoutputs**→`tools/call` `add_labels`
  
  ```json
  {"params":{"arguments":{"item_number":16,"labels":[{"confidence":"HIGH","name":"bot-triaged","rationale":"The issue lacks sufficient information to classify as bug, feature, or question."}]},"name":"add_labels"}}
  ```
- 🔍 rpc **safeoutputs**←`resp`
  
  ```json
  {"id":1,"result":{"content":[{"text":"{\"result\":\"success\"}","type":"text"}]}}
  ```
- 🔍 rpc **safeoutputs**→`tools/call` `{"jsonrpc":"2.0","method":"tools/call","params":{"arguments":{"body":"\u003e [!NOTE]\n\u003e Automated first-pass triage (AI-generated, not yet reviewed by a maintainer). Labels and suggestions may be wrong; a maintainer will confirm.\n\nThanks for the report. To triage this, could you share:\n\n- A minimal repro (a small, self-contained script or exact steps)\n- The full error message / stack trace\n- The output of `python -m torch.utils.collect_env`\n\n\u003csub\u003eTriage procedure: pytorch-issue-triage...`
- 🔍 rpc **safeoutputs**←`resp`
  
  ```json
  {"id":1,"result":{"content":[{"text":"{\"result\":\"success\",\"temporary_id\":\"aw_n5SwzpqA\",\"comment\":\"#aw_n5SwzpqA\"}","type":"text"}]}}
  ```

</details>
