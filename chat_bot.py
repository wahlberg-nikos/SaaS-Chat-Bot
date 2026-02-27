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
                api_version=os.getenv("AZURE_API_VERSION", "2024-12-01-preview"), # Updated to match your .env
                azure_endpoint=os.getenv("AZURE_ENDPOINT")
            )
            self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2-chat") # Updated to match your .env
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
        self.max_completion_tokens = 250 

    def get_response(self, user_input):
        suspicious_keywords = [
            "social security", "credit card number", "ssn", "bank account number", 
            "routing number", "cvv", "debit card", "passport number", 
            "driver's license", "drivers license", "private key", "bearer token"
        ]
        if any(keyword in user_input.lower() for keyword in suspicious_keywords):
            return "I cannot process messages containing highly sensitive personal data. Please remove this information."

        self.conversation_history.append({"role": "user", "content": user_input})
        trimmed_history = self.conversation_history[-self.max_history_window:]
        messages_payload = [self.system_prompt] + trimmed_history

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages_payload,
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens
            )
            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            return f"System Error: Connection failed. ({e})"


# --- STREAMLIT WEB UI ---

st.title("☁️ CloudScale SaaS Support")

# 1. Ask for the user's name if we don't have it yet
if "customer_name" not in st.session_state:
    with st.form("name_form"):
        name_input = st.text_input("Please enter your name to begin:")
        submitted = st.form_submit_button("Start Chat")
        if submitted:
            st.session_state.customer_name = name_input.strip() or "Valued Customer"
            st.rerun() # Refresh the page to load the chat
    st.stop() # Stop rendering the rest of the page until they enter a name

# 2. Initialize the Assistant in session_state so it remembers the history
if "assistant" not in st.session_state:
    st.session_state.assistant = SupportAssistant(customer_name=st.session_state.customer_name)
    initial_greeting = f"Hello {st.session_state.customer_name}! Welcome to CloudScale Support. I see you are on the Pro plan. How can I help you today?"
    st.session_state.assistant.conversation_history.append({"role": "assistant", "content": initial_greeting})

# 3. Sidebar with a reset button
with st.sidebar:
    st.markdown("### Support Controls")
    if st.button("Restart Chat"):
        del st.session_state.assistant # Delete the memory
        st.rerun() # Refresh the page

# 4. Draw the existing chat history to the screen
for msg in st.session_state.assistant.conversation_history:
    # Streamlit uses "user" and "assistant" roles natively!
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Handle new user input
if prompt := st.chat_input("Type your message here..."):
    # Draw the user's message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Show a spinner while the AI thinks, then draw the AI's response
    with st.chat_message("assistant"):
        with st.spinner("Agent is typing..."):
            response = st.session_state.assistant.get_response(prompt)
            st.markdown(response)