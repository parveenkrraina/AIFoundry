"""
Azure AI Foundry Agent Client for RAG
Handles AI response generation using Azure AI Foundry Agents
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Azure AI Foundry configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4")
API_VERSION = os.getenv("API_VERSION", "2024-02-15-preview")

# Global client instance (created once and reused)
_client = None


def initialize_agent():
    """
    Initialize the Azure OpenAI client for AI Foundry.
    This is called once and the client is reused for subsequent requests.
    """
    global _client
    
    if _client is not None:
        return _client
    
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        raise ValueError("Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY not configured")
    
    try:
        # Initialize the Azure OpenAI client (once)
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=API_VERSION
        )
        
        print(f"✅ Azure OpenAI client initialized")
        return _client
        
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {e}")
        raise


def generate_response(prompt, max_tokens=500, temperature=0.7):
    """
    Generate a response using Azure OpenAI.
    
    Args:
        prompt (str): The prompt including context and user query
        max_tokens (int): Maximum tokens in the response
        temperature (float): Sampling temperature (0-1)
        
    Returns:
        str: Generated response from the AI model
    """
    try:
        # Initialize client if needed
        client = initialize_agent()
        
        # Create chat completion
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful AI assistant that uses Microsoft Dataverse context to answer questions.

Your responsibilities:
1. Analyze the provided Dataverse context (tables, records, aggregates)
2. Provide accurate, concise answers grounded in that context
3. If the context does not fully answer the question, say so briefly and provide the best possible general guidance
4. When appropriate, cite specific fields or records from the context to support answers

Always maintain a professional and helpful tone."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract the response
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        else:
            return "No response generated from the model."
            
    except Exception as e:
        print(f"Error calling Azure OpenAI: {e}")
        return f"Error generating response: {str(e)}"


def cleanup_agent():
    """
    Clean up the client resources.
    Call this when shutting down the application.
    """
    global _client
    
    if _client:
        try:
            _client.close()
            print(f"✅ Azure OpenAI client cleaned up")
        except Exception as e:
            print(f"Warning: Error cleaning up client: {e}")
        finally:
            _client = None


if __name__ == "__main__":
    # Test the Azure OpenAI client
    test_prompt = """Context: Azure is a cloud computing platform that provides a wide range of services including compute, storage, networking, and AI services.

User Query: What is Azure?"""
    
    print(f"Testing Azure OpenAI Client with prompt:\n{test_prompt}\n")
    response = generate_response(test_prompt)
    print(f"Generated response:\n{response}")
    
    # Cleanup
    cleanup_agent()
