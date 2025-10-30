"""
RAG AI Agent - Main Entry Point
Combines Dataverse retrieval with Azure AI Foundry Agents
"""
import sys
import atexit
from dataverse_client import get_context_from_dataverse
from openai_client import generate_response, cleanup_agent

# Register cleanup on exit
atexit.register(cleanup_agent)


def rag_agent(user_query, verbose=True):
    """
    Process a user query using RAG (Retrieval-Augmented Generation).
    
    Args:
        user_query (str): The user's question or query
        verbose (bool): Whether to print detailed information
        
    Returns:
        str: The AI-generated response
    """
    if verbose:
        print(f"\n🔍 Retrieving context for: '{user_query}'")
    
    # Step 1: Retrieve relevant context from Dataverse
    context = get_context_from_dataverse(user_query)
    
    if verbose:
        print(f"\n📚 Retrieved Context:")
        print(f"{context[:200]}..." if len(context) > 200 else context)
    
    # Step 2: Construct prompt with context and query
    if context and context != "No relevant context found in Dataverse.":
        prompt = f"""Context from knowledge base:
{context}

User Question: {user_query}

Please provide a helpful and accurate answer based on the context above. If the context doesn't fully answer the question, provide the best possible response and acknowledge any limitations."""
    else:
        prompt = f"""User Question: {user_query}

Please provide a helpful response. Note: No specific context was found in the knowledge base."""
    
    if verbose:
        print(f"\n🤖 Generating response...")
    
    # Step 3: Generate response using Azure OpenAI
    response = generate_response(prompt)
    
    return response


def interactive_mode():
    """
    Run the agent in interactive mode for continuous queries.
    """
    print("=" * 60)
    print("RAG AI Agent - Interactive Mode")
    print("Powered by Dataverse + Azure OpenAI")
    print("=" * 60)
    print("\nType your questions (or 'exit' to quit)\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            response = rag_agent(user_input, verbose=True)
            print(f"\n🤖 Agent: {response}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def single_query_mode(query):
    """
    Process a single query and exit.
    
    Args:
        query (str): The user's question
    """
    response = rag_agent(query, verbose=True)
    print(f"\n🤖 Response:\n{response}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query mode: python main.py "your question here"
        query = " ".join(sys.argv[1:])
        single_query_mode(query)
    else:
        # Interactive mode
        interactive_mode()
