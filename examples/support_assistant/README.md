# Support Assistant Example: Node/Slice Design

This document defines the node composition and state slice contract for a support assistant workflow.
The intent is to create a runnable example under `examples/support_assistant/` later.

## State Slices

| Slice | Purpose | Key Fields (examples) |
| --- | --- | --- |
| `request` | Raw inbound request payload. | `text`, `user_id`, `locale`, `channel`, `metadata` |
| `support_ticket` | Drafted support ticket content. | `title`, `summary`, `category`, `priority`, `customer_context`, `escalation_reason` |
| `knowledge_base` | FAQ search results and metadata. | `matches` (list), `top_answer`, `confidence` |
| `response` | Final response to return. | `response_type`, `response_data` |
| `_internal` | Workflow control flags. | `intent`, `route`, `needs_human`, `trace` |

### Slice Notes

- `request` is immutable from node to node; nodes should read it but not overwrite it.
- `support_ticket` is accumulated and refined by downstream nodes.
- `knowledge_base` holds only derived data from FAQs.
- `_internal` is used for routing decisions (e.g., `intent`, `needs_human`).

## Node Definitions

### IntentRouterNode

**Goal:** Decide intent from `request` and set workflow flags.

**NodeContract**

- **reads:** `request`, `_internal`
- **writes:** `_internal`

**Writes (examples):**

```json
{
  "intent": "faq" | "ticket" | "escalate",
  "route": "faq_search" | "ticket_draft" | "escalation",
  "needs_human": false
}
```

**Triggering:**

- First node in the flow (no `_internal` intent set).

---

### FAQSearchNode

**Goal:** Search a hard-coded FAQ list and return candidate answers.

**NodeContract**

- **reads:** `request`, `_internal`
- **writes:** `knowledge_base`, `_internal`

**Writes (examples):**

```json
{
  "knowledge_base": {
    "matches": [
      {"question": "...", "answer": "...", "score": 0.82}
    ],
    "top_answer": "...",
    "confidence": 0.82
  },
  "_internal": {
    "route": "response"
  }
}
```

**Triggering:**

- When `_internal.intent == "faq"` and `_internal.route == "faq_search"`.

---

### TicketDraftNode

**Goal:** Generate a support ticket draft from the request and any context.

**NodeContract**

- **reads:** `request`, `_internal`, `knowledge_base`, `support_ticket`
- **writes:** `support_ticket`, `_internal`

**Writes (examples):**

```json
{
  "support_ticket": {
    "title": "Login issue",
    "summary": "User cannot log in since password reset...",
    "category": "authentication",
    "priority": "high",
    "customer_context": {"user_id": "..."}
  },
  "_internal": {
    "route": "escalation_check"
  }
}
```

**Triggering:**

- When `_internal.intent == "ticket"` and `_internal.route == "ticket_draft"`.

---

### EscalationNode

**Goal:** Decide whether to switch to human handling based on conditions.

**NodeContract**

- **reads:** `request`, `_internal`, `support_ticket`, `knowledge_base`
- **writes:** `_internal`, `support_ticket`

**Writes (examples):**

```json
{
  "_internal": {
    "needs_human": true,
    "route": "response"
  },
  "support_ticket": {
    "escalation_reason": "billing dispute"
  }
}
```

**Triggering:**

- After `TicketDraftNode` or `FAQSearchNode`, when `_internal.route == "escalation_check"` or `"escalation"`.

---

### ResponseComposerNode

**Goal:** Compose the final response from available slices.

**NodeContract**

- **reads:** `request`, `_internal`, `knowledge_base`, `support_ticket`
- **writes:** `response`

**Writes (examples):**

```json
{
  "response": {
    "response_type": "faq" | "ticket" | "escalated",
    "response_data": {
      "message": "...",
      "ticket_id": null
    }
  }
}
```

**Triggering:**

- Terminal node when `_internal.route == "response"`.

## Suggested Routing Logic

1. **IntentRouterNode** → sets `_internal.intent` and `_internal.route`.
2. **FAQSearchNode** (if intent is FAQ) → sets `knowledge_base` and `_internal.route = "response"`.
3. **TicketDraftNode** (if intent is ticket) → sets `support_ticket` and `_internal.route = "escalation_check"`.
4. **EscalationNode** → sets `_internal.needs_human`, `support_ticket.escalation_reason`, and `_internal.route = "response"`.
5. **ResponseComposerNode** → uses `needs_human` + other slices to choose `response_type`.
