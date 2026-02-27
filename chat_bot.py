import os
import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Set up the web page title and icon
st.set_page_config(page_title="CloudScale Support", page_icon="☁️", layout="centered")

class SupportAssistant:
    def __init__(self, customer_name="Customer"):
        # Setup Azure OpenAI
        try:
            self.client = AzureOpenAI(
                api_key=os.getenv("AZURE_API_KEY"),
                api_version=os.getenv("AZURE_API_VERSION", "2024-12-01-preview"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT")
            )
            self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2-chat")
        except Exception as e:
            st.error(f"Error initializing Azure OpenAI client: {e}")
            st.stop()

        # Faux Knowledge Base & Guardrails
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are a customer support agent for 'CloudScale', a B2B cloud storage SaaS product. "
                "Your tone must always be calm, polite, professional, and empathetic. "
                "\n\n--- CLOUDSCALE KNOWLEDGE BASE --- "
                "Pricing Tiers: Basic ($10/mo), Pro ($30/mo), Enterprise ($100/mo). "
                "Refund Policy: Refunds are only allowed within 14 days of the last charge. "
                "Password Reset: Direct users to www.cloudscale.com/reset. "
                "Current System Status: All systems operational. "
                f"\n\n--- CURRENT USER METADATA --- "
                f"User Name: {customer_name} | Plan: Pro | Account Status: Active "
                "\n\n--- GUARDRAILS AND RESTRICTIONS --- "
                "1. CREDENTIALS: If a user asks for passwords, API keys, or credentials, MUST REFUSE politely. "
                "2. ABUSE: If the user is angry, frustrated, or abusive, respond empathetically and neutrally. "
                "3. OUT OF SCOPE: If the user asks for legal or financial advice, redirect to legal@cloudscale.com."
            )
        }
        
        self.conversation_history = []
        self.max_history_window = 6
        self.temperature = 1 
        self.max_completion_tokens = 2500 # Increased for better reasoning responses

    def get_response(self, user_input):
        suspicious_keywords = [
            "social security", "credit card number", "ssn", "bank account number", 
            "routing number", "cvv", "debit card", "passport number", 
            "driver's license", "drivers license", "private key", "bearer token"
        ]
        
        if any(keyword in user_input.lower() for keyword in suspicious_keywords):
            # Return a simple string; the UI loop will handle strings vs streams
            return "I cannot process messages containing highly sensitive personal data. Please remove this information."

        self.conversation_history.append({"role": "user", "content": user_input})
        trimmed_history = self.conversation_history[-self.max_history_window:]
        messages_payload = [self.system_prompt] + trimmed_history

        try:
            # Note: We return the stream object itself
            return self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages_payload,
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                stream=True  # ENABLE STREAMING
            )
        except Exception as e:
            return f"System Error: Connection failed. ({e})"


# --- STREAMLIT WEB UI ---

st.title("☁️ CloudScale SaaS Support")

# 1. Session Initialization (Ask for name)
if "customer_name" not in st.session_state:
    with st.form("name_form"):
        name_input = st.text_input("Please enter your name to begin:")
        submitted = st.form_submit_button("Start Chat")
        if submitted:
            # Handle 'exit' or 'restart' edge cases at name prompt
            if name_input.lower().strip() == "exit":
                st.info("Goodbye! Have a great day.")
                st.stop()
            elif name_input.lower().strip() in ["restart", "clear"]:
                st.warning("We haven't started yet! Please enter your name.")
            else:
                st.session_state.customer_name = name_input.strip() or "Valued Customer"
                st.rerun()
    st.stop()

# 2. Initialize the Assistant
if "assistant" not in st.session_state:
    st.session_state.assistant = SupportAssistant(customer_name=st.session_state.customer_name)
    initial_greeting = f"Hello {st.session_state.customer_name}! Welcome to CloudScale Support. I see you are on the Pro plan. How can I help you today?"
    st.session_state.assistant.conversation_history.append({"role": "assistant", "content": initial_greeting})

# 3. Sidebar
with st.sidebar:
    st.markdown("### Support Controls")
    if st.button("Restart Chat"):
        del st.session_state.assistant
        del st.session_state.customer_name
        st.rerun()

# 4. Display Chat History
for msg in st.session_state.assistant.conversation_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Handle Chat Input
if prompt := st.chat_input("Type your message here..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Handle response with streaming effect
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        result = st.session_state.assistant.get_response(prompt)
        
        # Check if result is a stream or an error/guardrail string
        if isinstance(result, str):
            full_response = result
            response_placeholder.markdown(full_response)
        else:
            # Iterate through the stream chunks
            for chunk in result:
                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        full_response += content
                        # Add a blinking cursor effect
                        response_placeholder.markdown(full_response + "▌")
            
            # Remove cursor and show final response
            response_placeholder.markdown(full_response)
            
        # Save the final response to conversation history
        st.session_state.assistant.conversation_history.append({"role": "assistant", "content": full_response})