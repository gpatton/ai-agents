import { useCallback, useEffect, useRef, useState } from "react";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
  useAuth,
} from "@clerk/clerk-react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function ConversationList() {
  const { getToken } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] =
    useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [input, setInput] = useState("");
  const [message, setMessage] = useState("Loading Conversations ..");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const messagesEndRef = useRef(null);
  const requestInProgressRef = useRef(false);
  const abortControllerRef = useRef(null);
  const activeReplyRef = useRef(null);

  const [toolEvents, setToolEvents] = useState([]);
  const [requestId, setRequestId] = useState("");

  const [evaluations, setEvaluations] = useState([]);
  const [evaluationMessage, setEvaluationMessage] = useState("");
  const [refreshingEvaluations, setRefreshingEvaluations] =
    useState(false);

  async function getApiToken() {
    const token = await getToken({
      template: "agentforge-api",
    });

    if (!token) {
      throw new Error("Could not obtain an API token.");
    }

    return token;
  }

  const loadConversations = useCallback(async () => {
    try {
      const token = await getToken({
        template: "agentforge-api",
      });

      if (!token) {
        throw new Error("Could not obtain an API token.");
      }

      const response = await fetch(`${API_URL}/conversations`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}.`);
      }

      const data = await response.json();

      setConversations(data);

      setMessage(
        data.length === 0
          ? "You have no conversations yet."
          : ""
      );
    } catch (error) {
      setMessage(error.message);
    }
  }, [getToken]);

  const loadEvaluations = useCallback(async () => {
    setRefreshingEvaluations(true);

    try {
      const token = await getToken({
        template: "agentforge-api",
      });

      if (!token) {
        throw new Error(
          "Could not obtain an API token."
        );
      }

      const response = await fetch(
        `${API_URL}/evaluations`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Evaluations API returned HTTP ${response.status}.`
        );
      }

      const data = await response.json();

      setEvaluations(data);

      setEvaluationMessage(
        data.length === 0
          ? "No evaluation reports found."
          : `✓ Refreshed ${new Date().toLocaleTimeString()}`
      );
    } catch (error) {
      setEvaluationMessage(error.message);
    } finally {
      setRefreshingEvaluations(false);
    }
  }, [getToken]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    void loadEvaluations();
  }, [loadEvaluations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [chatMessages, sending]);

  async function createNewConversation() {
    if (
      requestInProgressRef.current ||
      loadingHistory
    ) {
      return;
    }

    setMessage("Creating conversation...");

    try {
      const token = await getApiToken();

      const response = await fetch(
        `${API_URL}/conversations`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: "New AgentForge conversation",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `API returned HTTP ${response.status}.`
        );
      }

      const conversation = await response.json();

      setConversations((current) => [
        conversation,
        ...current,
      ]);

      setSelectedConversation(conversation);
      setChatMessages([]);
      setInput("");
      setMessage("Conversation created successfully!");
    } catch (error) {
      setMessage(error.message);
    }
  }

  const createNewConversationRef =
    useRef(createNewConversation);

  useEffect(() => {
    createNewConversationRef.current =
      createNewConversation;
  });

  useEffect(() => {
    function handleKeyDown(event) {
      if (
        event.altKey &&
        event.shiftKey &&
        event.key.toLowerCase() === "n"
      ) {
        event.preventDefault();
        void createNewConversationRef.current();
      }
    }

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, []);

  async function deleteConversation(conversation) {
    if (sending || loadingHistory) {
      return;
    }

    const confirmed = window.confirm(
      `Permanently delete "${conversation.title}" and its messages?`
    );

    if (!confirmed) {
      return;
    }

    try {
      const token = await getApiToken();

      const response = await fetch(
        `${API_URL}/conversations/${conversation.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `API returned HTTP ${response.status}.`
        );
      }

      setConversations((current) =>
        current.filter(
          (item) => item.id !== conversation.id
        )
      );

      if (
        selectedConversation?.id === conversation.id
      ) {
        setSelectedConversation(null);
        setChatMessages([]);
        setInput("");
      }

      setMessage(
        "Conversation deleted successfully."
      );
    } catch (error) {
      setMessage(
        `Could not delete conversation: ${error.message}`
      );
    }
  }

  async function renameConversation(conversation) {
    if (sending || loadingHistory) {
      return;
    }

    const newTitle = window.prompt(
      "Enter a new conversation title:",
      conversation.title
    );

    if (
      newTitle === null ||
      !newTitle.trim()
    ) {
      return;
    }

    try {
      const token = await getApiToken();

      const response = await fetch(
        `${API_URL}/conversations/${conversation.id}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: newTitle.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `API returned HTTP ${response.status}.`
        );
      }

      const updatedConversation =
        await response.json();

      setConversations((current) =>
        current.map((item) =>
          item.id === updatedConversation.id
            ? updatedConversation
            : item
        )
      );

      setSelectedConversation((current) =>
        current?.id === updatedConversation.id
          ? updatedConversation
          : current
      );

      setMessage(
        "Conversation renamed successfully!"
      );
    } catch (error) {
      setMessage(
        `Could not rename conversation: ${error.message}`
      );
    }
  }

  async function selectConversation(conversation) {
    if (sending || loadingHistory) {
      return;
    }

    setSelectedConversation(conversation);
    setChatMessages([]);
    setToolEvents([]);
    setRequestId("");
    setInput("");
    setLoadingHistory(true);
    setMessage(
      "Loading conversation history..."
    );

    try {
      const token = await getApiToken();

      const response = await fetch(
        `${API_URL}/conversations/${conversation.id}/messages`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `API returned HTTP ${response.status}.`
        );
      }

      const data = await response.json();

      setChatMessages(data.messages);
      setMessage("");
    } catch (error) {
      setMessage(
        `Could not load messages: ${error.message}`
      );
    } finally {
      setLoadingHistory(false);
    }
  }

  async function requestReply({
    userText,
    conversationId,
    retryIndex = null,
  }) {
    if (
      requestInProgressRef.current ||
      loadingHistory
    ) {
      return;
    }

    const controller =
      new AbortController();

    abortControllerRef.current =
      controller;

    requestInProgressRef.current = true;

    activeReplyRef.current = {
      retryIndex,
      userText,
      conversationId,
    };

    setSending(true);
    setMessage("");
    setToolEvents([]);
    setRequestId("");

    if (retryIndex === null) {
      setChatMessages((current) => [
        ...current,
        {
          role: "user",
          content: userText,
        },
        {
          role: "assistant",
          content: "",
        },
      ]);
    } else {
      setChatMessages((current) =>
        current.map((item, index) =>
          index === retryIndex
            ? {
                role: "assistant",
                content: "",
              }
            : item
        )
      );
    }

    let streamedText = "";
    let completed = false;
    let buffer = "";

    function updateReply(reply) {
      if (controller.signal.aborted) {
        return;
      }

      setChatMessages((current) => {
        const index =
          retryIndex === null
            ? current.length - 1
            : retryIndex;

        if (!current[index]) {
          return current;
        }

        const updated = [...current];

        updated[index] = reply;

        return updated;
      });
    }

    function processLine(line) {
      if (!line.trim()) {
        return;
      }

      const event = JSON.parse(line);

      if (controller.signal.aborted) {
        return;
      }

      if (event.request_id) {
        setRequestId(event.request_id);
      }

      if (event.type === "text") {
        streamedText += event.content ?? "";

        updateReply({
          role: "assistant",
          content: streamedText,
        });
      } else if (
        [
          "tool_start",
          "tool_end",
          "tool_error",
        ].includes(event.type)
      ) {
        setToolEvents((current) => [
          ...current,
          event,
        ]);
      } else if (event.type === "done") {
        completed = true;
      } else if (event.type === "error") {
        throw new Error(
          event.message ||
            "Agent request failed."
        );
      }
    }

    try {
      const token = await getApiToken();

      if (controller.signal.aborted) {
        return;
      }

      const response = await fetch(
        `${API_URL}/chat/events`,
        {
          method: "POST",
          signal: controller.signal,
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userText,
            session_id: conversationId,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `API returned HTTP ${response.status}.`
        );
      }

      if (!response.body) {
        throw new Error(
          "The API did not return a readable stream."
        );
      }

      const reader =
        response.body.getReader();

      const decoder =
        new TextDecoder();

      while (true) {
        const { done, value } =
          await reader.read();

        if (controller.signal.aborted) {
          return;
        }

        if (done) {
          break;
        }

        buffer += decoder.decode(
          value,
          { stream: true }
        );

        const lines = buffer.split("\n");

        buffer = lines.pop() ?? "";

        for (const line of lines) {
          processLine(line);
        }
      }

      buffer += decoder.decode();

      if (controller.signal.aborted) {
        return;
      }

      if (buffer.trim()) {
        processLine(buffer);
      }

      if (!completed) {
        throw new Error(
          "The event stream ended before completion."
        );
      }

      if (!streamedText.trim()) {
        throw new Error(
          "The agent returned an empty response."
        );
      }

      updateReply({
        role: "assistant",
        content: streamedText,
      });
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      updateReply({
        role: "assistant",
        content: streamedText
          ? `${streamedText}\n\nResponse interrupted: ${error.message}`
          : `Sorry, I couldn't generate a reply. ${error.message}`,
        failed: true,
        retryText: userText,
        retryConversationId:
          conversationId,
      });
    } finally {
      if (
        abortControllerRef.current ===
        controller
      ) {
        abortControllerRef.current = null;
        activeReplyRef.current = null;
      }

      requestInProgressRef.current = false;
      setSending(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();

    if (
      !selectedConversation ||
      !input.trim() ||
      requestInProgressRef.current ||
      loadingHistory
    ) {
      return;
    }

    const userText = input.trim();

    const conversationId =
      selectedConversation.id;

    setInput("");

    await requestReply({
      userText,
      conversationId,
    });
  }

  function stopGenerating() {
    const controller =
      abortControllerRef.current;

    const active =
      activeReplyRef.current;

    if (
      !controller ||
      controller.signal.aborted ||
      !active
    ) {
      return;
    }

    controller.abort();

    setChatMessages((current) => {
      if (!current.length) {
        return current;
      }

      const updated = [...current];

      const replyIndex =
        active.retryIndex === null
          ? updated.length - 1
          : active.retryIndex;

      const reply =
        updated[replyIndex];

      if (
        !reply ||
        reply.role !== "assistant"
      ) {
        return current;
      }

      updated[replyIndex] = {
        role: "assistant",
        content: reply.content
          ? `${reply.content}\n\n[Request stopped — partial response]`
          : "Request stopped.",
        failed: true,
        retryText: active.userText,
        retryConversationId:
          active.conversationId,
      };

      return updated;
    });
  }

  async function retryMessage(
    chatMessage,
    index
  ) {
    if (
      !chatMessage.failed ||
      !chatMessage.retryText ||
      !selectedConversation ||
      chatMessage.retryConversationId !==
        selectedConversation.id ||
      requestInProgressRef.current ||
      loadingHistory
    ) {
      return;
    }

    const confirmed = window.confirm(
      "Retry this message? If the previous request reached the server, " +
        "retrying may save a duplicate message."
    );

    if (!confirmed) {
      return;
    }

    await requestReply({
      userText: chatMessage.retryText,
      conversationId:
        chatMessage.retryConversationId,
      retryIndex: index,
    });
  }

  /*
   * Evaluation summary
   *
   * Only live evaluations are used for the latest
   * evaluation summary. Older/manual reports remain
   * available in the history section.
   */

  const liveEvaluations =
    evaluations.filter((evaluation) =>
      evaluation.test_name?.startsWith(
        "live_"
      )
    );

  const latestEvaluations =
    Object.values(
      liveEvaluations.reduce(
        (latest, evaluation) => {
          const current =
            latest[evaluation.test_name];

          if (
            !current ||
            new Date(evaluation.timestamp) >
              new Date(current.timestamp)
          ) {
            latest[evaluation.test_name] =
              evaluation;
          }

          return latest;
        },
        {}
      )
    ).sort(
      (a, b) =>
        new Date(b.timestamp) -
        new Date(a.timestamp)
    );

  const latestPassed =
    latestEvaluations.filter(
      (evaluation) => evaluation.passed
    ).length;

  const latestEvaluationFilenames =
    new Set(
      latestEvaluations.map(
        (evaluation) => evaluation.filename
      )
    );

  const previousEvaluations =
    evaluations.filter(
      (evaluation) =>
        !latestEvaluationFilenames.has(
          evaluation.filename
        )
    );

  return (
    <section className="agentforge-layout">
      <aside className="conversation-sidebar">
        <h2>My conversations</h2>

        <button
          type="button"
          className="new-conversation-button"
          title="New conversation (Alt + Shift + N)"
          onClick={createNewConversation}
          disabled={
            sending || loadingHistory
          }
        >
          <span aria-hidden="true">
            ＋
          </span>
          New conversation
        </button>

        <p>{message}</p>

        <ul>
          {conversations.map(
            (conversation) => (
              <li key={conversation.id}>
                <button
                  className={
                    selectedConversation?.id ===
                    conversation.id
                      ? "conversation-title active"
                      : "conversation-title"
                  }
                  onClick={() =>
                    selectConversation(
                      conversation
                    )
                  }
                  disabled={
                    sending ||
                    loadingHistory
                  }
                >
                  {conversation.title}
                </button>

                {" "}

                <button
                  onClick={() =>
                    renameConversation(
                      conversation
                    )
                  }
                  disabled={
                    sending ||
                    loadingHistory
                  }
                >
                  Rename
                </button>

                {" "}

                <button
                  onClick={() =>
                    deleteConversation(
                      conversation
                    )
                  }
                  disabled={
                    sending ||
                    loadingHistory
                  }
                >
                  Delete
                </button>
              </li>
            )
          )}
        </ul>

          <div className="evaluation-panel">
  <div className="evaluation-header">
    <h2>Evaluation Results</h2>

    <button
      type="button"
      className="evaluation-refresh-button"
      onClick={loadEvaluations}
      disabled={refreshingEvaluations}
    >
      {refreshingEvaluations
        ? "↻ Refreshing..."
        : "↻ Refresh"}
    </button>
  </div>

  {evaluationMessage && (
    <p>{evaluationMessage}</p>
  )}

  {latestEvaluations.length >
    0 && (
    <>
      <h3>Latest Results</h3>

              <p>
                <strong>
                  {latestPassed}/
                  {
                    latestEvaluations.length
                  }{" "}
                  passed
                </strong>
              </p>

              <ul>
                {latestEvaluations.map(
                  (evaluation) => (
                    <li
                      key={
                        evaluation.filename
                      }
                    >
<div>
  <span
    className={
      evaluation.passed
        ? "evaluation-status evaluation-pass"
        : "evaluation-status evaluation-fail"
    }
  >
{evaluation.passed ? (
  <>
    <span className="evaluation-icon evaluation-icon-pass">
      ✓
    </span>{" "}
    PASS
  </>
) : (
  <>
    <span className="evaluation-icon evaluation-icon-fail">
      ✗
    </span>{" "}
    FAIL
  </>
)}


  </span>
</div>
                      <div>
                        {evaluation.test_name
                          .replace(
                            /^live_/,
                            ""
                          )
                          .replaceAll(
                            "_",
                            " "
                          )}
                      </div>

                      <div>
                        Response:{" "}
                        {
                          evaluation.response_time_seconds
                        }
                        s
                      </div>

                      {evaluation.tool_executions?.map(
                        (
                          tool,
                          index
                        ) => (
                          <div
                            key={`${evaluation.filename}-${index}`}
                          >
                            Tool:{" "}
                            {tool.tool ??
                              "Unknown"}
                            {" — "}
                            {typeof tool.duration_ms ===
                            "number"
                              ? `${tool.duration_ms.toFixed(
                                  2
                                )} ms`
                              : "No timing"}
                          </div>
                        )
                      )}

                      <div>
                        <small>
                          {new Date(
                            evaluation.timestamp
                          ).toLocaleString()}
                        </small>
                      </div>
                    </li>
                  )
                )}
              </ul>

              <details>
                <summary>
                  Previous evaluation runs (
                  {previousEvaluations.length})
                </summary>

                <ul>
                  {previousEvaluations.map(
                    (evaluation) => (
                      <li
                        key={
                          evaluation.filename
                        }
                      >
                        <strong>
                          {evaluation.passed
                            ? "✓"
                            : "✗"}{" "}
                          {
                            evaluation.test_name
                          }
                        </strong>

                        {" — "}

                        {
                          evaluation.response_time_seconds
                        }
                        s

                        <div>
                          <small>
                            {new Date(
                              evaluation.timestamp
                            ).toLocaleString()}
                          </small>
                        </div>
                      </li>
                    )
                  )}
                </ul>
              </details>
            </>
          )}
        </div>
      </aside>

      <section className="chat-panel">
        {selectedConversation ? (
          <>
            <h2>
              {
                selectedConversation.title
              }
            </h2>

            <div className="chat-messages">
              {chatMessages.map(
                (chatMessage, index) => (
                  <p
                    key={
                      chatMessage.id ??
                      index
                    }
                    className={
                      chatMessage.role ===
                      "user"
                        ? "chat-message user-message"
                        : "chat-message assistant-message"
                    }
                  >
                    <strong>
                      {chatMessage.role ===
                      "user"
                        ? "You"
                        : "AgentForge"}
                      :
                    </strong>{" "}
                    {chatMessage.content}

                    {chatMessage.failed && (
                      <>
                        {" "}
                        <button
                          type="button"
                          className="retry-button"
                          onClick={() =>
                            retryMessage(
                              chatMessage,
                              index
                            )
                          }
                          disabled={
                            sending ||
                            loadingHistory
                          }
                        >
                          Retry
                        </button>
                      </>
                    )}
                  </p>
                )
              )}

              {sending &&
                chatMessages.at(-1)
                  ?.content === "" && (
                  <p className="chat-message assistant-message">
                    <strong>
                      AgentForge:
                    </strong>{" "}
                    Thinking…
                  </p>
                )}

              <div ref={messagesEndRef} />
            </div>
              <section
              className="tool-activity-panel"
              aria-label="Tool activity"
                        
              >
              <h3>Tool activity</h3>

              {requestId && (
                <p>
                  Request ID:{" "}
                  <code>
                    {requestId}
                  </code>
                </p>
              )}

              {toolEvents.length === 0 ? (
                <p>
                  No tool calls recorded
                  for this request.
                </p>
              ) : (
                <ol>
                  {toolEvents.map(
                    (event, index) => (
                       <li
  className={`tool-event ${
    event.type === "tool_start"
      ? "tool-event-start"
      : event.type === "tool_error" ||
        (event.type === "tool_end" &&
          String(event.output ?? "").includes(
            "status='error'"
          ))
      ? "tool-event-error"
      : "tool-event-complete"
  }`}
  key={`${
    event.run_id ?? "tool"
  }-${event.type}-${index}`}
> 
                       <strong>
                          {event.tool ??
                            "Unknown tool"}
                        </strong>
                        {" — "}

                        {event.type ===
                        "tool_start"
                          ? "Started"
                          : event.type ===
                              "tool_error" ||
                            (event.type ===
                              "tool_end" &&
                              String(
                                event.output ??
                                  ""
                              ).includes(
                                "status='error'"
                              ))
                          ? "Error"
                          : "Completed"}

                        {(event.type ===
                          "tool_end" ||
                          event.type ===
                            "tool_error") &&
                          typeof event.duration_ms ===
                            "number" && (
                            <span
                              style={{
                                marginLeft:
                                  "10px",
                                fontSize:
                                  "0.85rem",
                                color:
                                  "#16a34a",
                              }}
                            >
                              (
                              {event.duration_ms.toFixed(
                                2
                              )}{" "}
                              ms)
                            </span>
                          )}

                        {event.type ===
                          "tool_error" &&
                          event.error && (
                            <pre
                              style={{
                                whiteSpace:
                                  "pre-wrap",
                                overflowWrap:
                                  "anywhere",
                              }}
                            >
                              {
                                event.error
                              }
                            </pre>
                          )}

                        {event.type ===
                          "tool_start" &&
                          event.input && (
                            <details>
                              <summary>
                                Input
                              </summary>

                              <pre
                                style={{
                                  whiteSpace:
                                    "pre-wrap",
                                  overflowWrap:
                                    "anywhere",
                                }}
                              >
                                {
                                  event.input
                                }
                              </pre>
                            </details>
                          )}

                        {event.type ===
                          "tool_end" &&
                          event.output && (
                            <details>
                              <summary>
                                Result
                              </summary>

                              <pre
                                style={{
                                  whiteSpace:
                                    "pre-wrap",
                                  overflowWrap:
                                    "anywhere",
                                }}
                              >
                                {
                                  event.output
                                }
                              </pre>
                            </details>
                          )}
                      </li>
                    )
                  )}
                </ol>
              )}
            </section>

            <form
              className="chat-form"
              onSubmit={sendMessage}
            >
              <input
                className="chat-input"
                type="text"
                value={input}
                onChange={(event) =>
                  setInput(
                    event.target.value
                  )
                }
                placeholder="Ask AgentForge something..."
                disabled={
                  sending ||
                  loadingHistory
                }
              />

              <button
                type="button"
                className="clear-input-button"
                onClick={() =>
                  setInput("")
                }
                disabled={
                  !input ||
                  sending ||
                  loadingHistory
                }
              >
                Clear
              </button>

              {sending ? (
                <button
                  type="button"
                  onClick={
                    stopGenerating
                  }
                >
                  Stop generating
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={
                    loadingHistory ||
                    !input.trim()
                  }
                >
                  Send
                </button>
              )}
            </form>

            <p className="message-counter">
              {input.length} characters
            </p>
          </>
        ) : (
          <p>
            Select a conversation or
            create a new one to start
            chatting.
          </p>
        )}
      </section>
    </section>
  );
}

function App() {
  return (
    <main
      style={{
        padding: "40px",
        fontFamily: "Arial",
      }}
    >
      <h1>AgentForge</h1>

      <SignedOut>
        <p>
          Sign in to access your AI
          agent.
        </p>

        <SignInButton mode="modal">
          <button>Sign in</button>
        </SignInButton>
      </SignedOut>

      <SignedIn>
        <p>
          You are signed in to
          AgentForge.
        </p>

        <UserButton />

        <hr />

        <ConversationList />
      </SignedIn>
    </main>
  );
}

export default App;
