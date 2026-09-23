
import { useEffect, useRef, useState } from "react";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
  useAuth,
} from "@clerk/clerk-react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function ConversationList() {
  const { getToken } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] =
    useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [input, setInput] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const messagesEndRef = useRef(null);
  const requestInProgressRef = useRef(false);
  const abortControllerRef = useRef(null);

  async function getApiToken() {
    const token = await getToken({
      template: "agentforge-api",
    });

    if (!token) {
      throw new Error("Could not obtain an API token.");
    }

    return token;
  }

  async function loadConversations() {
    setMessage("Loading conversations...");

    try {
      const token = await getApiToken();

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
  }

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [chatMessages, sending]);

  async function createNewConversation() {
    if (requestInProgressRef.current || loadingHistory) {
      return;
    }

    setMessage("Creating conversation...");

    try {
      const token = await getApiToken();

      const response = await fetch(`${API_URL}/conversations`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: "New AgentForge conversation",
        }),
      });

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}.`);
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

  useEffect(() => {
    function handleKeyDown(event) {
      if (
        event.altKey &&
        event.shiftKey &&
        event.key.toLowerCase() === "n"
      ) {
        event.preventDefault();
        createNewConversation();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
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
        throw new Error(`API returned HTTP ${response.status}.`);
      }

      setConversations((current) =>
        current.filter((item) => item.id !== conversation.id)
      );

      if (selectedConversation?.id === conversation.id) {
        setSelectedConversation(null);
        setChatMessages([]);
        setInput("");
      }

      setMessage("Conversation deleted successfully.");
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

    if (newTitle === null || !newTitle.trim()) {
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
        throw new Error(`API returned HTTP ${response.status}.`);
      }

      const updatedConversation = await response.json();

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

      setMessage("Conversation renamed successfully!");
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
    setInput("");
    setLoadingHistory(true);
    setMessage("Loading conversation history...");

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
        throw new Error(`API returned HTTP ${response.status}.`);
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
    if (requestInProgressRef.current || loadingHistory) return;

    const controller = new AbortController();
    abortControllerRef.current = controller;
    requestInProgressRef.current = true;
    setSending(true);
    setMessage("");

    // The last message is the in-progress reply for new requests.
    // A retry reuses its existing failed reply instead.
    if (retryIndex === null) {
      setChatMessages((current) => [
        ...current,
        { role: "user", content: userText },
        { role: "assistant", content: "" },
      ]);
    } else {
      setChatMessages((current) =>
        current.map((item, index) =>
          index === retryIndex
            ? { role: "assistant", content: "" }
            : item
        )
      );
    }

    let streamedText = "";

    function updateReply(reply) {
      if (controller.signal.aborted) return;
      setChatMessages((current) => {
        const index = retryIndex === null ? current.length - 1 : retryIndex;
        if (!current[index]) return current;
        const updated = [...current];
        updated[index] = reply;
        return updated;
      });
    }

    try {
      const token = await getApiToken();
      if (controller.signal.aborted) return;

      const response = await fetch(`${API_URL}/chat/stream`, {
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
      });

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}.`);
      }
      if (!response.body) {
        throw new Error("The API did not return a readable stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (controller.signal.aborted) return;
        if (done) break;
        streamedText += decoder.decode(value, { stream: true });
        updateReply({ role: "assistant", content: streamedText });
      }
      streamedText += decoder.decode();
      if (controller.signal.aborted) return;
      if (!streamedText.trim()) {
        throw new Error("The agent returned an empty response.");
      }
      updateReply({ role: "assistant", content: streamedText });
    } catch (error) {
      if (controller.signal.aborted) return;
      updateReply({
        role: "assistant",
        content: streamedText
          ? `${streamedText}\n\nResponse interrupted: ${error.message}`
          : `Sorry, I couldn't generate a reply. ${error.message}`,
        failed: true,
        retryText: userText,
        retryConversationId: conversationId,
      });
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
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
    const conversationId = selectedConversation.id;

    setInput("");

    await requestReply({
      userText,
      conversationId,
    });
  }

  function stopGenerating() {
    const controller = abortControllerRef.current;
    if (!controller || controller.signal.aborted) return;

    controller.abort();
    setChatMessages((current) => {
      if (!current.length) return current;
      const updated = [...current];
      const replyIndex = updated.length - 1;
      const reply = updated[replyIndex];
      if (reply.role !== "assistant") return current;

      const lastUserMessage = [...updated]
        .reverse()
        .find((item) => item.role === "user");

      updated[replyIndex] = {
        role: "assistant",
        content: reply.content
          ? `${reply.content}\n\n[Request stopped — partial response]`
          : "Request stopped.",
        failed: true,
        retryText: lastUserMessage?.content ?? "",
        retryConversationId: selectedConversation?.id,
      };
      return updated;
    });
  }

  async function retryMessage(chatMessage, index) {
    if (
      !chatMessage.failed ||
      !chatMessage.retryText ||
      !selectedConversation ||
      chatMessage.retryConversationId !== selectedConversation.id ||
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
      conversationId: chatMessage.retryConversationId,
      retryIndex: index,
    });
  }

  return (
    <section className="agentforge-layout">
      <aside className="conversation-sidebar">
        <h2>My conversations</h2>


        {" "}

<button
  type="button"
  className="new-conversation-button"
  title="New conversation (Alt + Shift + N)"
  onClick={createNewConversation}
  disabled={sending || loadingHistory}
>
  <span aria-hidden="true">＋</span>
  New conversation
</button>
        <p>{message}</p>

        <ul>
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                className={
                  selectedConversation?.id === conversation.id
                    ? "conversation-title active"
                    : "conversation-title"
                }
                onClick={() =>
                  selectConversation(conversation)
                }
                disabled={sending || loadingHistory}
              >
                {conversation.title}
              </button>

              {" "}

              <button
                onClick={() =>
                  renameConversation(conversation)
                }
                disabled={sending || loadingHistory}
              >
                Rename
              </button>

              {" "}

              <button
                onClick={() =>
                  deleteConversation(conversation)
                }
                disabled={sending || loadingHistory}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat-panel">
        {selectedConversation ? (
          <>
            <h2>{selectedConversation.title}</h2>

            <div className="chat-messages">
              {chatMessages.map((chatMessage, index) => (
                <p
                  key={chatMessage.id ?? index}
                  className={
                    chatMessage.role === "user"
                      ? "chat-message user-message"
                      : "chat-message assistant-message"
                  }
                >
                  <strong>
                    {chatMessage.role === "user"
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
                          retryMessage(chatMessage, index)
                        }
                        disabled={sending || loadingHistory}
                      >
                        Retry
                      </button>
                    </>
                  )}
                </p>
              ))}

              {sending && chatMessages.at(-1)?.content === "" && (
                <p className="chat-message assistant-message">
                  <strong>AgentForge:</strong> Thinking…
                </p>
              )}

              <div ref={messagesEndRef} />
            </div>

            <form
              className="chat-form"
              onSubmit={sendMessage}
            >
              <input
                className="chat-input"
                type="text"
                value={input}
                onChange={(event) =>
                  setInput(event.target.value)
                }
                placeholder="Ask AgentForge something..."
                disabled={sending || loadingHistory}
              />

              <button
                type="button"
                className="clear-input-button"
                onClick={() => setInput("")}
                disabled={!input || sending || loadingHistory}
              >
                Clear
              </button>

              {sending ? (
                <button
                  type="button"
                  onClick={stopGenerating}
                >
                  Stop generating
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={loadingHistory || !input.trim()}
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
            Select a conversation or create a new one
            to start chatting.
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
        <p>Sign in to access your AI agent.</p>

        <SignInButton mode="modal">
          <button>Sign in</button>
        </SignInButton>
      </SignedOut>

      <SignedIn>
        <p>You are signed in to AgentForge.</p>

        <UserButton />

        <hr />

        <ConversationList />
      </SignedIn>
    </main>
  );
}

export default App;
