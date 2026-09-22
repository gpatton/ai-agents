import { useEffect, useState } from "react";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
  useAuth,
} from "@clerk/clerk-react";

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

      const response = await fetch(
        `${API_URL}/conversations`,
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

  async function createNewConversation() {
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

  async function selectConversation(conversation) {
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
      setMessage(`Could not load messages: ${error.message}`);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();

    if (
      !selectedConversation ||
      !input.trim() ||
      sending ||
      loadingHistory
    ) {
      return;
    }

    const conversationId = selectedConversation.id;
    const userText = input.trim();

    setSending(true);
    setMessage("");
    setInput("");

    setChatMessages((current) => [
      ...current,
      {
        role: "user",
        content: userText,
      },
    ]);

    try {
      const token = await getApiToken();

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
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

      const data = await response.json();

      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.response,
        },
      ]);
    } catch (error) {
      setMessage(`Could not send message: ${error.message}`);
    } finally {
      setSending(false);
    }
  }

  return (
    <section>
      <h2>My conversations</h2>

      <button onClick={loadConversations}>
        Load conversations
      </button>

      {" "}

      <button onClick={createNewConversation}>
        New conversation
      </button>

      <p>{message}</p>

      <ul>
        {conversations.map((conversation) => (
          <li key={conversation.id}>
            <button
              onClick={() => selectConversation(conversation)}
              disabled={sending || loadingHistory}
            >
              {conversation.title}
            </button>
          </li>
        ))}
      </ul>

      {selectedConversation && (
        <section>
          <hr />

          <h2>{selectedConversation.title}</h2>

          <div>
            {chatMessages.map((chatMessage, index) => (
              <p key={chatMessage.id ?? index}>
                <strong>
                  {chatMessage.role === "user"
                    ? "You"
                    : "AgentForge"}
                  :
                </strong>

                {" "}

                {chatMessage.content}
              </p>
            ))}
          </div>

          <form onSubmit={sendMessage}>
            <input
              type="text"
              value={input}
              onChange={(event) =>
                setInput(event.target.value)
              }
              placeholder="Ask AgentForge something..."
              disabled={sending || loadingHistory}
              style={{
                width: "300px",
                padding: "8px",
              }}
            />

            <button
              type="submit"
              disabled={
                sending ||
                loadingHistory ||
                !input.trim()
              }
            >
              {sending ? "Sending..." : "Send"}
            </button>
          </form>
        </section>
      )}
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
