# AgentForge demo walkthrough

This walkthrough demonstrates AgentForge running locally in the existing
kind cluster. Allow about five minutes.

## Prepare

Check the deployment:

```bash
kubectl --context=kind-agentforge get pods -n agentforge
```

Start the frontend port-forward and leave it running:

```bash
kubectl --context=kind-agentforge port-forward \
  -n agentforge service/agentforge-frontend 8081:80
```

Open http://127.0.0.1:8081 and sign in through Clerk.

## 1. Calculator and tool execution

Start a conversation and send:

> Use the calculator tool to multiply 25 by 48.

Check that the answer is 1,200. Show the tool details and streaming response.

## 2. Document retrieval

Send:

> According to the AgentForge employee handbook, how many days of paid
> annual leave do employees receive per year? Use search_documents.

Check that the answer states 25 days and show the document-search tool details.

## 3. Error recovery

Send:

> Use the calculator tool to divide 100 by 0. Explain the result.

Show how the agent explains the error without inventing a numerical answer.

## 4. Persistent history

Refresh the dashboard and reopen the conversation.
Show that previous messages remain available.

## 5. Evaluation reports

Open the evaluation results panel and show the existing reports.
These are previously saved results; viewing them does not run new evaluations.

## Engineering evidence

Explain the supporting implementation:

- FastAPI, LangGraph, and MCP for agent execution.
- Clerk authentication and PostgreSQL conversation storage.
- Chroma document retrieval.
- Request IDs and tool timing in structured logs.
- Docker Compose and local Kubernetes deployment.
- Git-tagged images, deployment and rollback scripts.
- Persistent storage and tested backup procedures.
- Automated tests and GitHub Actions.

On 5 October 2026, the test run reported 80 passed and 4 skipped.
The skipped cases required a Clerk test token or explicit live-evaluation opt-in.

## Scope

This release demonstrates a local application. Public hosting and
production operations are outside this portfolio release.
